export type StructurizrWorkspace = any; // We can type this later.

export type OrchestratorStatus = "busy" | "idle";

export type Role = "human" | "ai" | "system";

export type Message = {
    role: Role;
    content: string;
}

export type IncomingFrame =
  | { type: "orchestrator_status"; status: OrchestratorStatus }
  | { 
      type: "orchestrator_event"; 
      node: string;
      data: {
        execution_plan?: string;
        messages?: Message[];
        next_actor?: string;
        consecutive_worker_loops?: number;
      } 
    }
  | { type: "orchestrator_done" }
  | { type: "architecture_diagram"; node: string; workspace: StructurizrWorkspace }
  | { type: "question"; id: string; agent_name: string; question: string }
  | { type: "system"; level: "warn" | "error"; message: string }
  | AgentEvent;

export type OutgoingFrame =
  | { type: "user_input"; content: string }
  | { type: "reply"; id: string; response: string };

export type AgentEvent = {
  type: "agent_event";
  node: string;
  run_id: string;
  message_id: string;
  seq: number;
  timestamp: number;
  event: EventKind;
};

export type EventKind =
  | { kind: "reasoning"; content: string; delta: boolean }
  | { kind: "content";   content: string; delta: boolean }
  | { kind: "tool_call"; call_id: string; tool_name: string; args: unknown }
  | { kind: "tool_result"; call_id: string; tool_name: string; content: string; is_error?: boolean }
  | { kind: "telemetry"; model?: string; tokens_in?: number; tokens_out?: number; latency_ms?: number; cost_usd?: number }
  | { kind: "status"; phase: "started" | "waiting_for_tool" | "finished" | "cancelled" | "error"; detail?: string };
