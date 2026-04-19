import { useStore } from "@/lib/store";
import { TaskComposer } from "./TaskComposer";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./MessageBubble";

export function ChatView() {
  const { messages, inFlightEventBuffers, chatFilter } = useStore();
  const inFlightIds = Object.keys(inFlightEventBuffers);

  const displayMessages = chatFilter 
    ? messages.filter(m => m.node === chatFilter) 
    : messages;

  const displayInFlight = chatFilter 
    ? inFlightIds.filter(id => inFlightEventBuffers[id].node === chatFilter)
    : inFlightIds;

  return (
    <div className="absolute inset-0 flex flex-col">
      <ScrollArea className="flex-1 p-4">
        <div className="max-w-4xl mx-auto space-y-6 pb-24">
          {displayMessages.length === 0 && displayInFlight.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground pt-32">
              <p className="text-sm">No messages yet. Send a task to the orchestrator.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {displayMessages.map(msg => (
                <MessageBubble key={msg.id} msg={msg} />
              ))}
              
              {/* In-Flight Events */}
              {displayInFlight.map(id => {
                const msg = inFlightEventBuffers[id];
                return <MessageBubble key={msg.id} msg={msg} />
              })}
            </div>
          )}
        </div>
      </ScrollArea>
      
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-background via-background to-transparent z-10 pt-10">
        <div className="max-w-4xl mx-auto">
          <TaskComposer />
        </div>
      </div>
    </div>
  );
}
