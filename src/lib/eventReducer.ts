import { AgentEvent, EventKind } from "./protocol";

export interface TelemetryData {
  model?: string;
  tokens_in?: number;
  tokens_out?: number;
  latency_ms?: number;
  cost_usd?: number;
}

export interface ChatBlock {
  kind: "content" | "reasoning" | "tool_call" | "tool_result";
  content?: string;
  call_id?: string;
  tool_name?: string;
  args?: unknown;
  is_error?: boolean;
}

export interface ChatMessage {
  id: string; // run_id + message_id
  node: string;
  run_id: string;
  timestamp: number;
  blocks: ChatBlock[];
  telemetry?: TelemetryData;
  status: "started" | "waiting_for_tool" | "finished" | "cancelled" | "error";
  errorDetail?: string;
}

export function applyAgentEvent(state: any, frame: AgentEvent) {
  const msgId = `${frame.run_id}-${frame.message_id}`;
  const buffer = state.inFlightEventBuffers[msgId];
  
  if (!buffer) {
    // New message
    const newMsg: ChatMessage = {
      id: msgId,
      node: frame.node,
      run_id: frame.run_id,
      timestamp: frame.timestamp,
      blocks: [],
      status: "started"
    };
    return updateBuffer(state, msgId, processEvent(newMsg, frame.event));
  }

  // Existing message
  return updateBuffer(state, msgId, processEvent(buffer, frame.event));
}

function updateBuffer(state: any, msgId: string, updatedMsg: ChatMessage) {
  if (updatedMsg.status === "finished" || updatedMsg.status === "cancelled" || updatedMsg.status === "error") {
      const nextBuffers = { ...state.inFlightEventBuffers };
      delete nextBuffers[msgId];
      // dedupe existing if re-arrived
      const filtered = state.messages.filter((m: ChatMessage) => m.id !== msgId);
      return {
          inFlightEventBuffers: nextBuffers,
          messages: [...filtered, updatedMsg],
          activeNodes: { ...state.activeNodes, [updatedMsg.node]: true }
      };
  }

  return {
      inFlightEventBuffers: {
          ...state.inFlightEventBuffers,
          [msgId]: updatedMsg
      },
      activeNodes: { ...state.activeNodes, [updatedMsg.node]: true }
  };
}

function processEvent(msg: ChatMessage, event: EventKind): ChatMessage {
  const next = { ...msg, blocks: [...msg.blocks] };

  switch (event.kind) {
    case "content":
    case "reasoning": {
      const lastBlock = next.blocks[next.blocks.length - 1];
      if (lastBlock && lastBlock.kind === event.kind && event.delta) {
        lastBlock.content = (lastBlock.content || "") + event.content;
      } else {
        next.blocks.push({ kind: event.kind, content: event.content });
      }
      break;
    }
    case "tool_call":
      next.blocks.push({ kind: "tool_call", call_id: event.call_id, tool_name: event.tool_name, args: event.args });
      break;
    case "tool_result":
      next.blocks.push({ kind: "tool_result", call_id: event.call_id, tool_name: event.tool_name, content: event.content, is_error: event.is_error });
      break;
    case "telemetry":
      next.telemetry = { ...next.telemetry, ...event };
      break;
    case "status":
      next.status = event.phase;
      if (event.detail) next.errorDetail = event.detail;
      break;
  }

  return next;
}
