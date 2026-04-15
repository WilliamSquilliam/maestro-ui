"""Sidecar HTTP server for individual worker containers.

Provides:
  - POST /execute         -- synchronous workflow execution
  - POST /execute/stream  -- SSE streaming of workflow events (non-blocking)
  - GET  /health          -- health check
"""
import json
import asyncio
import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

sidecar_app = FastAPI(title="Maestro Worker Sidecar")


class ExecuteRequest(BaseModel):
    prompt: str
    context: Optional[str] = None


# --- GET /health ---
@sidecar_app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


# --- POST /execute ---
@sidecar_app.post("/execute")
async def execute(req: ExecuteRequest):
    """Synchronous workflow execution.

    Runs the container workflow graph to completion and returns the result.
    """
    try:
        from container_state import container_app

        initial_state = {
            "execution_plan": req.prompt,
        }

        final_state = None
        for event in container_app.stream(initial_state, stream_mode="updates"):
            for node_name, node_state in event.items():
                if isinstance(node_state, dict):
                    final_state = node_state

        result_text = ""
        if final_state:
            result_text = final_state.get(
                "final_text",
                final_state.get(
                    "worker_output", "Workflow completed without producing output."
                ),
            )

        return JSONResponse(content={"text": result_text, "usage": {}})

    except Exception as e:
        logger.error(f"Container workflow execution error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


# --- POST /execute/stream ---
@sidecar_app.post("/execute/stream")
async def execute_stream(req: ExecuteRequest):
    """SSE streaming of workflow events.

    Streams node-level updates as the container workflow progresses, including
    actual content from foreman instructions, worker output, and review notes.

    Uses run_in_executor + async queue so the synchronous container_app.stream()
    does NOT block the event loop.
    """

    async def event_generator():
        loop = asyncio.get_running_loop()
        event_queue: asyncio.Queue = asyncio.Queue()

        def run_graph_sync():
            """Run the synchronous LangGraph stream in a thread."""
            final_text = ""
            try:
                from container_state import container_app

                initial_state = {
                    "execution_plan": req.prompt,
                }

                for event in container_app.stream(
                    initial_state, stream_mode="updates"
                ):
                    for node_name, node_state in event.items():
                        if not isinstance(node_state, dict):
                            continue

                        # Emit node transition event
                        loop.call_soon_threadsafe(
                            event_queue.put_nowait,
                            {
                                "type": "node_update",
                                "node": node_name,
                                "keys": list(node_state.keys()),
                            },
                        )

                        # Emit content for specific state keys
                        if (
                            "foreman_instructions" in node_state
                            and node_state["foreman_instructions"]
                        ):
                            loop.call_soon_threadsafe(
                                event_queue.put_nowait,
                                {
                                    "type": "foreman_instructions",
                                    "node": node_name,
                                    "content": node_state["foreman_instructions"],
                                },
                            )

                        if (
                            "worker_output" in node_state
                            and node_state["worker_output"]
                        ):
                            loop.call_soon_threadsafe(
                                event_queue.put_nowait,
                                {
                                    "type": "worker_output",
                                    "node": node_name,
                                    "content": node_state["worker_output"],
                                },
                            )

                        if (
                            "review_notes" in node_state
                            and node_state["review_notes"]
                        ):
                            loop.call_soon_threadsafe(
                                event_queue.put_nowait,
                                {
                                    "type": "review_notes",
                                    "node": node_name,
                                    "content": node_state["review_notes"],
                                },
                            )

                        # Status events
                        if "next_actor" in node_state:
                            loop.call_soon_threadsafe(
                                event_queue.put_nowait,
                                {
                                    "type": "routing",
                                    "node": node_name,
                                    "next_actor": node_state["next_actor"],
                                },
                            )

                        # Capture final text from the last state
                        if "final_text" in node_state:
                            final_text = node_state["final_text"]

                if not final_text:
                    final_text = "Workflow completed without producing final text."

            except Exception as e:
                logger.error(f"Container workflow streaming error: {e}")
                final_text = f"Error during container workflow execution: {str(e)}"
                loop.call_soon_threadsafe(
                    event_queue.put_nowait,
                    {"type": "error", "content": str(e)},
                )

            # Signal completion
            loop.call_soon_threadsafe(
                event_queue.put_nowait,
                {"type": "done", "text": final_text, "usage": {}},
            )

        # Start the synchronous graph in a background thread
        loop.run_in_executor(None, run_graph_sync)

        # Yield events as they arrive from the queue
        while True:
            try:
                event_data = await asyncio.wait_for(
                    event_queue.get(), timeout=300.0
                )
                yield f"data: {json.dumps(event_data)}\n\n"
                if event_data.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Workflow timed out'})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
