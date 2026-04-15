"""Sidecar HTTP server for individual worker containers.

Provides:
  - POST /execute         — synchronous workflow execution
  - POST /execute/stream  — SSE streaming of workflow events
  - GET  /health          — health check
"""
import json
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
    """

    async def event_generator():
        final_text = ""
        try:
            from container_state import container_app

            initial_state = {
                "execution_plan": req.prompt,
            }

            # Stream node-level updates
            for event in container_app.stream(initial_state, stream_mode="updates"):
                for node_name, node_state in event.items():
                    if not isinstance(node_state, dict):
                        continue

                    # Emit node transition event
                    yield f"data: {json.dumps({'type': 'node_update', 'node': node_name, 'keys': list(node_state.keys())})}\n\n"

                    # Emit content for specific state keys
                    if (
                        "foreman_instructions" in node_state
                        and node_state["foreman_instructions"]
                    ):
                        yield f"data: {json.dumps({'type': 'foreman_instructions', 'node': node_name, 'content': node_state['foreman_instructions']})}\n\n"

                    if (
                        "worker_output" in node_state
                        and node_state["worker_output"]
                    ):
                        yield f"data: {json.dumps({'type': 'worker_output', 'node': node_name, 'content': node_state['worker_output']})}\n\n"

                    if (
                        "review_notes" in node_state
                        and node_state["review_notes"]
                    ):
                        yield f"data: {json.dumps({'type': 'review_notes', 'node': node_name, 'content': node_state['review_notes']})}\n\n"

                    # Status events
                    if "next_actor" in node_state:
                        yield f"data: {json.dumps({'type': 'routing', 'node': node_name, 'next_actor': node_state['next_actor']})}\n\n"

                    # Capture final text from the last state
                    if "final_text" in node_state:
                        final_text = node_state["final_text"]

            if not final_text:
                final_text = "Workflow completed without producing final text."

        except Exception as e:
            logger.error(f"Container workflow streaming error: {e}")
            final_text = f"Error during container workflow execution: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # Final event with accumulated result
        yield f"data: {json.dumps({'type': 'done', 'text': final_text, 'usage': {}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
