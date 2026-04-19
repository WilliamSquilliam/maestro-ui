import { useState } from "react";
import { useMaestroSocket } from "@/lib/ws";
import { useStore } from "@/lib/store";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { SendHorizontal } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";

export function TaskComposer() {
  const [content, setContent] = useState("");
  const { send } = useMaestroSocket();
  const { status } = useStore();

  const isBusy = status === "busy";

  const handleSend = () => {
    if (!content.trim() || isBusy) return;
    
    send({ type: "user_input", content });
    setContent("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === "Escape") {
      setContent("");
    }
  };

  return (
    <div className="relative rounded-xl border border-border bg-card shadow-sm focus-within:ring-1 focus-within:ring-primary overflow-hidden transition-shadow">
      <Textarea 
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={isBusy ? "Orchestrator is busy..." : "Send a task to Maestro... (Cmd+Enter to send, /arch hints architect)"}
        className="min-h-[80px] resize-none border-0 focus-visible:ring-0 px-4 py-3 bg-transparent"
        disabled={isBusy}
      />
      <div className="flex justify-between items-center px-4 py-2 bg-muted/30 border-t border-border">
        <div className="text-xs text-muted-foreground flex items-center gap-4">
           <span><kbd className="font-mono bg-muted border border-border px-1 rounded mr-1">⌘</kbd> + <kbd className="font-mono bg-muted border border-border px-1 rounded mr-1">Enter</kbd> Send</span>
        </div>
        <TooltipProvider>
          <Tooltip>
            {/* @ts-expect-error React 19 typing mismatch with Radix UI */}
            <TooltipTrigger asChild>
               <span>
                  <Button size="icon" disabled={!content.trim() || isBusy} onClick={handleSend} className="h-8 w-8 rounded-full">
                    <SendHorizontal className="h-4 w-4" />
                  </Button>
               </span>
            </TooltipTrigger>
            <TooltipContent>
              {isBusy ? "Cannot send task while orchestrator is busy" : "Send Task"}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}
