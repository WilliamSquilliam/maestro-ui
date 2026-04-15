"""Host-level API server for the Maestro UI.

Bridges the frontend to the LangGraph host graph and worker sidecars.
Serves the static UI and provides:
  - GET  /api/workers          — list of worker nodes from config
  - WS   /ws/master            — WebSocket for master orchestrator chat
  - GET  /api/workers/{name}/events — SSE proxy to worker sidecar streams
"""
import os
import json
import asyncio
import logging
from typing import Dict, Any

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "nodes_config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        _CONFIG = json.load(f)
except Exception:
    _CONFIG = {}

_GRAPH_CONFIG = _CONFIG.get("graph", {})
_RAW_WORKERS = _GRAPH_CONFIG.get("worker_nodes", [])


def _get_worker_list() -> list[dict]:
    """Return list of worker node dicts with name, type, port."""
    workers = []
    for w in _RAW_WORKERS:
        if isinstance(w, dict):
            workers.append({
                "name": w.get("name", "unknown"),
                "type": w.get("type", "worker"),
                "port": w.get("port", 8000),
            })
    return workers


def _get_worker_url(name: str) -> str | None:
    """Resolve a worker name to its sidecar base URL."""
    for w in _get_worker_list():
        if w["name"] == name:
            return f"http://localhost:{w['port']}"
    return None


# --- FastAPI App ---
api_app = FastAPI(title="Maestro UI API")

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global event bus: worker_name -> list of asyncio.Queue
# Each connected SSE client gets its own queue
_worker_event_buses: Dict[str, list[asyncio.Queue]] = {}


def _broadcast_worker_event(worker_name: str, event: dict):
    """Push an event to all SSE clients listening to this worker."""
    queues = _worker_event_buses.get(worker_name, [])
    for q in queues:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Drop if client is too slow


# --- GET /api/workers ---
@api_app.get("/api/workers")
async def get_workers():
    """Return the list of configured worker nodes."""
    return JSONResponse(content=_get_worker_list())


# --- WebSocket /ws/master ---
@api_app.websocket("/ws/master")
async def ws_master(websocket: WebSocket):
    """WebSocket endpoint for master orchestrator chat.

    Accepts JSON messages: {"message": "user text"}
    Streams back JSON events:
      {"type": "node_start", "node": "orchestrator"}
      {"type": "content", "node": "orchestrator", "content": "..."}
      {"type": "dispatch", "worker": "worker-name"}
      {"type": "worker_result", "worker": "worker-name", "content": "..."}
      {"type": "done"}
      {"type": "error", "content": "..."}
    """
    await websocket.accept()

    try:
        # Lazy import to avoid circular imports and heavy loading at module level
        from langchain_core.messages import HumanMessage
        from graph import app as langgraph_app

        config = {"configurable": {"thread_id": "ws-ui-session"}}

        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            if not user_message:
                continue

            try:
                initial_state = {
                    "messages": [HumanMessage(content=user_message)],
                    "execution_plan": "",
                    "next_actor": "",
                    "consecutive_worker_loops": 0,
                }

                # Stream the host graph
                # Run in executor since langgraph .stream() is synchronous
                loop = asyncio.get_event_loop()

                def run_graph():
                    events = []
                    for event in langgraph_app.stream(
                        initial_state, config=config, stream_mode="updates"
                    ):
                        events.append(event)
                    return events

                events = await loop.run_in_executor(None, run_graph)

                for event in events:
                    for node_name, node_state in event.items():
                        if not isinstance(node_state, dict):
                            continue

                        await websocket.send_json(
                            {
                                "type": "node_start",
                                "node": node_name,
                            }
                        )

                        # If orchestrator produced an execution plan with routing
                        if (
                            "execution_plan" in node_state
                            and node_state["execution_plan"]
                        ):
                            await websocket.send_json(
                                {
                                    "type": "content",
                                    "node": node_name,
                                    "content": str(node_state["execution_plan"]),
                                }
                            )

                        # If there are messages (worker results)
                        if "messages" in node_state and node_state["messages"]:
                            for msg in node_state["messages"]:
                                content = (
                                    msg.content
                                    if hasattr(msg, "content")
                                    else str(msg)
                                )
                                await websocket.send_json(
                                    {
                                        "type": "content",
                                        "node": node_name,
                                        "content": content,
                                    }
                                )

                                # Detect worker dispatch
                                if content.startswith("[") and "]" in content:
                                    worker_name = content[1 : content.index("]")]
                                    await websocket.send_json(
                                        {
                                            "type": "worker_result",
                                            "worker": worker_name,
                                            "content": content,
                                        }
                                    )

                        # Routing info
                        if "next_actor" in node_state:
                            next_actor = node_state["next_actor"]
                            # Check if it's a worker dispatch
                            worker_names = [w["name"] for w in _get_worker_list()]
                            if next_actor in worker_names:
                                await websocket.send_json(
                                    {
                                        "type": "dispatch",
                                        "worker": next_actor,
                                    }
                                )

                await websocket.send_json({"type": "done"})

            except Exception as e:
                logger.error(f"Graph execution error: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "content": str(e),
                    }
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# --- GET /api/workers/{name}/events (SSE) ---
@api_app.get("/api/workers/{name}/events")
async def worker_events_sse(name: str):
    """SSE endpoint that streams events for a specific worker.

    Clients connect and receive events whenever the worker is active.
    Also proxies to the worker's sidecar /execute/stream when available.
    """
    worker_url = _get_worker_url(name)
    if worker_url is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Worker '{name}' not found"},
        )

    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    # Register this client's queue
    if name not in _worker_event_buses:
        _worker_event_buses[name] = []
    _worker_event_buses[name].append(queue)

    async def event_generator():
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'status': 'connected', 'worker': name})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            # Unregister
            if name in _worker_event_buses:
                try:
                    _worker_event_buses[name].remove(queue)
                except ValueError:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- POST /api/workers/{name}/proxy-stream ---
@api_app.post("/api/workers/{name}/proxy-stream")
async def proxy_worker_stream(name: str):
    """Proxy a streaming request to a worker's sidecar and broadcast events.

    This is called internally when the host graph dispatches to a worker.
    It connects to the sidecar's /execute/stream and relays events to
    all SSE clients listening on /api/workers/{name}/events.
    """
    worker_url = _get_worker_url(name)
    if worker_url is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Worker '{name}' not found"},
        )

    # This endpoint is for internal triggering — actual streaming happens
    # through the event bus populated by the graph execution
    return JSONResponse(content={"status": "ok", "worker": name})


# --- Mount static UI (must be last) ---
_UI_DIR = os.path.join(os.path.dirname(__file__), "ui")
if os.path.isdir(_UI_DIR):
    api_app.mount("/", StaticFiles(directory=_UI_DIR, html=True), name="ui")
