import { create } from "zustand";
import { IncomingFrame, StructurizrWorkspace, OrchestratorStatus, AgentEvent } from "./protocol";
import { applyAgentEvent, ChatMessage } from "./eventReducer";

export interface MaestroState {
  status: OrchestratorStatus;
  diagram: StructurizrWorkspace | null;
  pendingQuestions: Record<string, { agent_name: string; question: string }>;
  messages: ChatMessage[];
  inFlightEventBuffers: Record<string, ChatMessage>;
  loopLimit: { max: number; current: number };
  activeNodes: Record<string, boolean>;

  chatFilter: string | null;
  setChatFilter: (node: string | null) => void;
  archTab: "c1" | "c2" | "c3" | "c4";
  setArchTab: (tab: "c1" | "c2" | "c3" | "c4") => void;

  handleIncoming: (frame: IncomingFrame) => void;
  removeQuestion: (id: string) => void;
  clearChat: () => void;
}

export const useStore = create<MaestroState>((set) => ({
  status: "idle",
  diagram: null,
  pendingQuestions: {},
  messages: [],
  inFlightEventBuffers: {},
  loopLimit: { max: 3, current: 0 },
  activeNodes: {},
  chatFilter: null,
  setChatFilter: (node) => set({ chatFilter: node }),
  archTab: "c1",
  setArchTab: (tab) => set({ archTab: tab }),

  handleIncoming: (frame) => set((state) => {
    switch(frame.type) {
      case "orchestrator_status":
        return { status: frame.status };
      case "orchestrator_event": {
        // Handle legacy flat messages and metadata
        const newNodes = { ...state.activeNodes, [frame.node]: true };
        const updates = { activeNodes: newNodes, loopLimit: { ...state.loopLimit } };
        if (frame.data.consecutive_worker_loops !== undefined) {
          updates.loopLimit.current = frame.data.consecutive_worker_loops;
        }

        const legacyMessages = frame.data.messages?.map((m, i) => ({
            id: `legacy-${Date.now()}-${i}`,
            node: frame.node,
            run_id: "legacy",
            timestamp: Date.now(),
            blocks: [{ kind: "content" as const, content: m.content }],
            status: "finished" as const
        })) || [];

        return {
            ...updates,
            messages: [...state.messages, ...legacyMessages]
        };
      }
      case "orchestrator_done":
        return { status: "idle" };
      case "architecture_diagram":
        return { diagram: frame.workspace, activeNodes: { ...state.activeNodes, [frame.node]: true } };
      case "question":
        return { pendingQuestions: { ...state.pendingQuestions, [frame.id]: { agent_name: frame.agent_name, question: frame.question } } };
      case "system":
        // Toasts can handle this globally via an effect listening to a stream, or we map to state if retained.
        return {}; 
      case "agent_event":
        return applyAgentEvent(state, frame);
      default:
        return {};
    }
  }),

  removeQuestion: (id) => set((state) => {
    const next = { ...state.pendingQuestions };
    delete next[id];
    return { pendingQuestions: next };
  }),

  clearChat: () => set({ messages: [], inFlightEventBuffers: {} })
}));
