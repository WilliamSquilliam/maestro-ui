import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChatMessage, ChatBlock } from "@/lib/eventReducer";
import { Terminal, Database, Wrench, FunctionSquare, Loader2, Waypoints } from "lucide-react";

export function MessageBubble({ msg }: { msg: ChatMessage }) {
  return (
    <Card className="p-4 shadow-sm border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border/50">
        <Badge variant="secondary" className="font-mono text-[10px] uppercase tracking-wider">
          {msg.node}
        </Badge>
        <span className="text-xs text-muted-foreground font-mono opacity-50">
           {new Date(msg.timestamp).toLocaleTimeString()}
        </span>
        {msg.status === "started" || msg.status === "waiting_for_tool" ? (
          <span className="ml-auto text-xs text-primary flex items-center gap-1.5 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" />
            {msg.status === "waiting_for_tool" ? "Running tool..." : "Thinking..."}
          </span>
        ) : null}
      </div>
      
      <div className="flex flex-col gap-4">
        {msg.blocks.map((block, idx) => (
          <MessageBlock key={idx} block={block} />
        ))}
      </div>

      {msg.status === "error" && msg.errorDetail && (
        <div className="mt-4 p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2">
           <Terminal className="w-4 h-4 shrink-0" />
           <p className="font-mono text-xs">{msg.errorDetail}</p>
        </div>
      )}

      {msg.telemetry && (
         <div className="mt-4 pt-3 border-t border-border/50 text-[10px] text-muted-foreground flexitems-center gap-4 font-mono opacity-70">
            {msg.telemetry.model && <span>Model: {msg.telemetry.model}</span>}
            {msg.telemetry.latency_ms && <span>Latency: {msg.telemetry.latency_ms}ms</span>}
            {msg.telemetry.tokens_in && <span>In: {msg.telemetry.tokens_in}</span>}
            {msg.telemetry.tokens_out && <span>Out: {msg.telemetry.tokens_out}</span>}
         </div>
      )}
    </Card>
  );
}

function MessageBlock({ block }: { block: ChatBlock }) {
  if (block.kind === "reasoning") {
    return (
      <div className="pl-3 border-l-2 border-primary/30 text-muted-foreground italic text-sm">
         <div className="prose prose-sm dark:prose-invert prose-p:my-1 opacity-80">
           <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {block.content || ""}
           </ReactMarkdown>
         </div>
      </div>
    );
  }

  if (block.kind === "tool_call") {
    return (
      <div className="bg-secondary/50 rounded-md p-3 font-mono text-xs border border-border/50">
        <div className="flex items-center gap-2 text-foreground font-semibold mb-2">
           <Wrench className="w-3.5 h-3.5 text-primary" />
           {block.tool_name}
        </div>
        <pre className="overflow-x-auto text-muted-foreground ml-5">
           {JSON.stringify(block.args, null, 2)}
        </pre>
      </div>
    );
  }

  if (block.kind === "tool_result") {
    if (block.call_id === "dispatch") {
      return (
        <div className="bg-primary/20 rounded-md p-3 font-mono text-xs border border-primary/40 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
             <Waypoints className="w-3.5 h-3.5 text-primary" />
             <span className="font-semibold text-primary opacity-90">Graph Routing</span>
          </div>
          <pre className="overflow-x-auto text-primary/90 pl-5 whitespace-pre-wrap break-all">
             {block.content}
          </pre>
        </div>
      );
    }
    return (
      <div className={`bg-muted/30 rounded-md p-3 font-mono text-xs border ${block.is_error ? 'border-destructive/30 bg-destructive/5' : 'border-border'}`}>
        <div className="flex items-center gap-2 mb-2">
           <Database className={`w-3.5 h-3.5 ${block.is_error ? 'text-destructive' : 'text-emerald-500'}`} />
           <span className="opacity-70">Result</span>
        </div>
        <pre className="overflow-x-auto max-h-48 pl-5 whitespace-pre-wrap break-all opacity-80">
           {block.content}
        </pre>
      </div>
    );
  }

  return (
    <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-pre:bg-code-bg prose-pre:border prose-pre:border-border">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {block.content || ""}
      </ReactMarkdown>
    </div>
  );
}
