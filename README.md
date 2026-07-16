# Maestro UI

The web interface for [Maestro](https://github.com/WilliamSquilliam/maestro) — a LangGraph-powered multi-agent orchestration system. Maestro UI connects to a running Maestro host over WebSocket and visualizes the orchestrator and its container-node agents in real time: live agent activity and telemetry, the evolving C4 architecture diagram, and human-in-the-loop prompts.

## Stack

- **React 19 + TypeScript + Vite**
- **Tailwind CSS + shadcn/ui** (Base UI primitives)
- **React Flow** (`@xyflow/react`) + **elkjs** for the architecture diagram
- **Zustand** for state, **react-use-websocket** for the live connection
- **Sonner** for toasts

## How it connects

The app opens a single WebSocket to the Maestro host (default `ws://localhost:8001/ws`, defined in [`src/lib/ws.ts`](src/lib/ws.ts)). It receives orchestrator status, `agent_event` telemetry, human-in-the-loop `question`, and `architecture_diagram` frames, and sends user input and question replies. The Maestro host must be running for the UI to have anything to display.

## Getting started

```bash
npm install
npm run dev        # start the Vite dev server, then open the printed local URL
```

Other scripts:

```bash
npm run build      # type-check and build for production
npm run preview    # preview the production build
npm run lint       # run ESLint
```

> The WebSocket URL is currently hardcoded in [`src/lib/ws.ts`](src/lib/ws.ts). Point it at your Maestro host if it isn't running on `localhost:8001`.
