import { useStore } from "@/lib/store";
import { useMaestroSocket } from "@/lib/ws";
import { ReadyState } from "react-use-websocket";
import { Badge } from "@/components/ui/badge";

export function TopBar() {
  const { status } = useStore();
  const { readyState } = useMaestroSocket();

  const isConnected = readyState === ReadyState.OPEN;

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-border bg-card shrink-0">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold tracking-tight text-primary">Maestro Control</h1>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-xs text-muted-foreground">{isConnected ? "Connected" : "Disconnected"}</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {status === "busy" ? (
          <Badge variant="secondary" className="animate-pulse bg-primary/20 text-primary">Orchestrator Busy</Badge>
        ) : (
          <Badge variant="outline" className="text-muted-foreground">Idle</Badge>
        )}
        <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-xs font-mono bg-muted rounded border border-border text-muted-foreground cursor-pointer hover:bg-secondary">
          <span className="text-xs">⌘</span>K
        </kbd>
      </div>
    </header>
  );
}
