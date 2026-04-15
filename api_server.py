"""Host-level API server for the Maestro UI.

Bridges the frontend to the LangGraph host graph and sidecar containers.
Serves the static UI, provides a WebSocket for master orchestrator chat,
and SSE endpoints that proxy worker container streaming events.
"""
import os
import json
import asyncio
import logging
from typing import Dict, Set
from collections import defaultdict

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "nodes_config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        NODE_CONFIG = json.load(f)
except Exception:
    NODE_CONFIG = {}

graph_config = NODE_CONFIG.get("graph", {})
raw_worker_nodes = graph_config.get("worker_nodes", [])

# Build a lookup: worker_name -> {name, type, port}
WORKER_INFO: Dict[str, dict] = {}
for node in raw_worker_nodes:
    if isinstance(node, dict):
        name = node["name"]
        WORKER_INFO[name] = {
            "name": name,
            "type": node.get("type", "worker"),
            "port": node.get("port", 8000),
        }

# ---------------------------------------------------------------------------
# Worker event bus -- per-worker, per-client async queues
# ---------------------------------------------------------------------------
# Maps worker_name -> set of asyncio.Queue (one per connected SSE client)
_worker_subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)


def _broadcast_worker_event(worker_name: str, event_data: dict):
    """Push an event to all SSE clients subscribed to a given worker.

    This is called from:
    1. The WebSocket handler when graph events relate to a worker (dispatch, results)
    2. The sidecar proxy task when relaying streaming events from a container
    """
    event_json = json.dumps(event_data)
    dead_queues = []
    for q in _worker_subscribers.get(worker_name, set()):
        try:
            q.put_nowait(event_json)
        except asyncio.QueueFull:
            dead_queues.append(q)
    for q in dead_queues:
        _worker_subscribers[worker_name].discard(q)


async def _proxy_sidecar_stream(worker_name: str, prompt: str):
    """Connect to a worker's sidecar /execute/stream SSE endpoint and relay events.

    This runs as a background task when the orchestrator dispatches to a worker.
    It uses httpx to open an SSE connection and pipes events through _broadcast_worker_event().
    """
    info = WORKER_INFO.get(worker_name)
    if not info:
        _broadcast_worker_event(worker_name, {
            "type": "error",
            "content": f"Unknown worker: {worker_name}",
        })
        return

    port = info["port"]
    url = f"http://localhost:{port}/execute/stream"

    _broadcast_worker_event(worker_name, {
        "type": "status",
        "status": "working",
        "content": f"Connecting to sidecar on port {port}...",
    })

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
            async with client.stream("POST", url, json={"prompt": prompt}) as response:
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        for line in event_str.strip().split("\n"):
                            if line.startswith("data: "):
                                data_str = line[6:]
                                try:
                                    event_data = json.loads(data_str)
                                    # Relay the sidecar event to all subscribed UI clients
                                    _broadcast_worker_event(worker_name, event_data)
                                except json.JSONDecodeError:
                                    _broadcast_worker_event(worker_name, {
                                        "type": "agent_stream",
                                        "content": data_str,
                                    })
    except httpx.ConnectError:
        _broadcast_worker_event(worker_name, {
            "type": "error",
            "content": f"Cannot connect to sidecar at {url}",
        })
    except Exception as e:
        _broadcast_worker_event(worker_name, {
            "type": "error",
            "content": f"Sidecar proxy error: {str(e)}",
        })
    finally:
        _broadcast_worker_event(worker_name, {
            "type": "status",
            "status": "idle",
            "content": "Worker finished",
        })


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
api_app = FastAPI(title="Maestro UI API")

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@api_app.get("/api/workers")
async def get_workers():
    """Return the list of worker nodes from nodes_config.json."""
    return JSONResponse(content={"workers": list(WORKER_INFO.values())})


@api_app.websocket("/ws/master")
async def master_websocket(ws: WebSocket):
    """WebSocket endpoint for master orchestrator chat.

    Accepts user messages, invokes the LangGraph host graph, and streams
    back orchestrator responses IN REAL-TIME using a queue-based bridge
    (not collect-all-then-send).
    """
    await ws.accept()
    logger.info("Master WebSocket client connected")

    try:
        while True:
            # Wait for user message
            data = await ws.receive_text()
            msg = json.loads(data)
            user_text = msg.get("message", "")
            if not user_text:
                continue

            # Import graph here to avoid circular imports at module level
            from graph import app as langgraph_app
            from langchain_core.messages import HumanMessage

            # Queue-based bridge for real-time streaming
            event_queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def run_graph():
                """Run the synchronous LangGraph in a thread, pushing events to queue."""
                try:
                    config = {"configurable": {"thread_id": "ui-session"}}
                    initial_state = {
                        "messages": [HumanMessage(content=user_text)],
                        "execution_plan": "",
                        "next_actor": "",
                        "consecutive_worker_loops": 0,
                    }
                    for event in langgraph_app.stream(
                        initial_state, config=config, stream_mode="updates"
                    ):
                        # Put each event on the queue as it's produced
                        loop.call_soon_threadsafe(event_queue.put_nowait, ("event", event))
                except Exception as e:
                    loop.call_soon_threadsafe(event_queue.put_nowait, ("error", str(e)))
                finally:
                    loop.call_soon_threadsafe(event_queue.put_nowait, ("done", None))

            # Start graph execution in background thread
            loop.run_in_executor(None, run_graph)

            # Process events from queue as they arrive and send to WebSocket
            while True:
                msg_type, payload = await event_queue.get()

                if msg_type == "done":
                    await ws.send_json({"type": "graph_done"})
                    break
                elif msg_type == "error":
                    await ws.send_json({"type": "error", "content": payload})
                    break
                elif msg_type == "event":
                    event = payload
                    for node_name, node_state in event.items():
                        if not isinstance(node_state, dict):
                            continue

                        # Send node activation to master panel
                        ws_event = {
                            "type": "node_update",
                            "node": node_name,
                            "keys": list(node_state.keys()),
                        }

                        # Include execution plan content if present
                        if "execution_plan" in node_state and node_state["execution_plan"]:
                            ws_event["execution_plan"] = str(
                                node_state["execution_plan"]
                            )[:2000]

                        # Include routing decision
                        if "next_actor" in node_state:
                            ws_event["next_actor"] = node_state["next_actor"]

                        # Include messages
                        if "messages" in node_state and node_state["messages"]:
                            msg_contents = []
                            for m in node_state["messages"]:
                                content = (
                                    m.content if hasattr(m, "content") else str(m)
                                )
                                msg_contents.append(content)
                            ws_event["messages"] = msg_contents

                        await ws.send_json(ws_event)

                        # CRITICAL: Wire up _broadcast_worker_event
                        # When orchestrator routes to a worker, notify that worker's
                        # panel and start the sidecar proxy
                        orchestrator_name = graph_config.get(
                            "orchestrator", "orchestrator"
                        )
                        if node_name == orchestrator_name:
                            next_actor = node_state.get("next_actor", "")
                            if next_actor in WORKER_INFO:
                                # Notify worker panel of dispatch
                                _broadcast_worker_event(next_actor, {
                                    "type": "status",
                                    "status": "working",
                                    "content": "Dispatched by orchestrator",
                                })
                                # Extract the execution plan for the sidecar
                                plan = node_state.get("execution_plan", user_text)
                                # Start sidecar proxy as background task
                                asyncio.create_task(
                                    _proxy_sidecar_stream(next_actor, plan)
                                )

                        # When a worker node returns results, broadcast to its panel
                        if node_name in WORKER_INFO:
                            worker_msgs = node_state.get("messages", [])
                            for m in worker_msgs:
                                content = (
                                    m.content
                                    if hasattr(m, "content")
                                    else str(m)
                                )
                                _broadcast_worker_event(node_name, {
                                    "type": "result",
                                    "content": content,
                                })

    except WebSocketDisconnect:
        logger.info("Master WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Master WebSocket error: {e}")
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.close(code=1011)


@api_app.get("/api/workers/{name}/events")
async def worker_events(name: str):
    """SSE endpoint for a specific worker's streaming events.

    Each connected client gets its own queue. Events are pushed by
    _broadcast_worker_event() which is called from:
    - The WebSocket handler (dispatch notifications, worker results)
    - The sidecar proxy (_proxy_sidecar_stream)
    """
    if name not in WORKER_INFO:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown worker: {name}"},
        )

    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _worker_subscribers[name].add(queue)

    async def event_generator():
        try:
            # Send initial connected status
            yield f"data: {json.dumps({'type': 'status', 'status': 'connected', 'worker': name})}\n\n"

            while True:
                try:
                    # Wait for event with timeout for keepalive
                    event_json = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {event_json}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _worker_subscribers[name].discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@api_app.get("/health")
async def health():
    return {"status": "ok"}


# Mount static UI files -- MUST be last (catch-all)
_ui_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.isdir(_ui_dir):
    api_app.mount("/", StaticFiles(directory=_ui_dir, html=True), name="ui")
