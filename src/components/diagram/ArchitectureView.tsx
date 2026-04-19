import { useStore } from "@/lib/store";

export function ArchitectureView() {
  const { diagram, archTab } = useStore();

  const labels: Record<string, string> = {
    c1: "C1 Context",
    c2: "C2 Containers",
    c3: "C3 Components",
    c4: "C4 Code"
  };

  return (
    <div className="absolute inset-0 flex flex-col p-4">
      <div className="text-xl font-bold tracking-tight mb-4">{labels[archTab]}</div>
      <div className="flex-1 border border-border rounded-lg bg-card/30 relative">
        {!diagram ? (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground flex-col gap-2">
            <p>Architect hasn't drawn anything yet.</p>
            <div className="text-xs">Send <code className="bg-secondary px-1 py-0.5 rounded">/arch design a plan for this system</code></div>
          </div>
        ) : (
          <div className="h-full w-full flex items-center justify-center text-muted-foreground">
            {/* React Flow View for {archTab} */}
            Rendering {labels[archTab]}...
          </div>
        )}
      </div>
    </div>
  );
}
