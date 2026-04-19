# Maestro WebSocket Protocol Contract

This document provides the authoritative specification for all JSON frames exchanged over the Maestro Control UI WebSocket (`ws://localhost:8001/ws`). Use this to implement the backend broadcaster and receiver.

## 1. Server → Client (Broadcasting Events)

The backend must emit these frames to the UI. All frames are JSON objects with a `type` discriminator.

### Orchestrator Status
Controls the "Busy/Idle" indicator and locks the task composer.
```json
{ "type": "orchestrator_status", "status": "busy" | "idle" }
```

### Orchestrator Metadata (Legacy/Summary)
Sent by the main graph to update high-level state.
```json
{
  "type": "orchestrator_event",
  "node": "string",
  "data": {
    "execution_plan": "string (optional)",
    "messages": [{ "role": "human" | "ai" | "system", "content": "string" }],
    "next_actor": "string (optional)",
    "consecutive_worker_loops": "number (optional)"
  }
}
```

### Architecture Diagram
Pushes a Structurizr Workspace JSON to the diagramming tool.
```json
{
  "type": "architecture_diagram",
  "node": "string",
  "workspace": {} // Structurizr JSON Workspace
}
```

### Human-in-the-Loop Question
Triggers a modal dialog in the UI.
```json
{
  "type": "question",
  "id": "string (unique interaction id)",
  "agent_name": "string",
  "question": "string"
}
```

### System Alerts
```json
{
  "type": "system",
  "level": "warn" | "error",
  "message": "string"
}
```

### Orchestrator Done
Resets the UI state for the next run.
```json
{ "type": "orchestrator_done" }
```

---

## 2. The `agent_event` (Real-time Streaming)

The UI expects granular events from individual agents to support token-by-token streaming and collapsible tool blocks.

```json
{
  "type": "agent_event",
  "node": "string",
  "run_id": "string",     // Correlates a specific orchestration run
  "message_id": "string", // Correlates chunks within a single message bubble
  "seq": "number",        // Monotonic sequence for ordering
  "timestamp": "number",  // Unix ms
  "event": EventKind
}
```

### EventKind Shapes:

**Reasoning Chunk:**
```json
{ "kind": "reasoning", "content": "chunk", "delta": true }
```

**Content Chunk:**
```json
{ "kind": "content", "content": "chunk", "delta": true }
```

**Tool Call:**
```json
{ "kind": "tool_call", "call_id": "unique_id", "tool_name": "name", "args": {} }
```

**Tool Result:**
```json
{ "kind": "tool_result", "call_id": "unique_id", "tool_name": "name", "content": "str", "is_error": false }
```

**Telemetry:**
```json
{ "kind": "telemetry", "model": "str", "tokens_in": 0, "tokens_out": 0, "latency_ms": 0, "cost_usd": 0 }
```

**Status/Phase:**
```json
{ "kind": "status", "phase": "started" | "waiting_for_tool" | "finished" | "cancelled" | "error", "detail": "error message" }
```

---

## 3. Client → Server (User Actions)

The backend should listen for these frames.

### User Input
Sent when the user submits a task from the composer.
```json
{ "type": "user_input", "content": "string" }
```

### Question Reply
Sent when the user answers a `question` frame from the modal.
```json
{ "type": "reply", "id": "id_from_question_frame", "response": "string" }
```
