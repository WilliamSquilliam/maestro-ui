import { MessageSquare, Boxes, Component, Box, Database, FileCode2 } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStore } from "@/lib/store";

interface LeftNavProps {
  activeTab: "chat" | "architecture";
  setActiveTab: (tab: "chat" | "architecture") => void;
}

export function LeftNav({ activeTab, setActiveTab }: LeftNavProps) {
  const { loopLimit, pendingQuestions, activeNodes, chatFilter, setChatFilter, archTab, setArchTab } = useStore();
  const rawNodes = Object.keys(activeNodes);
  
  const nodes = rawNodes;

  const pendingCount = Object.keys(pendingQuestions).length;

  return (
    <aside className="w-64 border-r border-border bg-card/50 flex flex-col hidden md:flex shrink-0">
      <div className="p-4 border-b border-border">
        <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as "chat" | "architecture")} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="chat" className="text-xs">
              <MessageSquare className="w-4 h-4 mr-2" />
              Chat
              {pendingCount > 0 && (
                <span className="ml-2 bg-primary text-primary-foreground text-[10px] px-1.5 py-0.5 rounded-full">
                  {pendingCount}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="architecture" className="text-xs">
              <Boxes className="w-4 h-4 mr-2" />
              Arch
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="flex-1 p-4 flex flex-col gap-6 overflow-y-auto">
        {activeTab === "chat" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Chat Windows</h3>
              <ul className="space-y-1">
                <li
                  className={`flex items-center gap-2 text-sm px-2 py-1.5 rounded cursor-pointer transition-colors ${chatFilter === null ? 'bg-secondary text-foreground' : 'text-foreground/80 hover:bg-secondary/50'}`}
                  onClick={() => setChatFilter(null)}
                >
                  <span className="w-2 h-2 rounded-full bg-primary/40" />
                  All Messages
                </li>
                {nodes.map(node => (
                  <li 
                    key={node} 
                    className={`flex items-center gap-2 px-2 py-1.5 rounded text-sm cursor-pointer transition-colors ${chatFilter === node ? 'bg-secondary text-foreground' : 'text-foreground/80 hover:bg-secondary/50'}`}
                    onClick={() => setChatFilter(node)}
                  >
                    <span className={`w-2 h-2 rounded-full ${chatFilter === node ? 'bg-primary' : 'bg-primary/40'}`} />
                    {node}
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Loop Guard</h3>
              <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
                <div 
                  className={`h-full transition-all ${
                     loopLimit.current >= loopLimit.max ? 'bg-destructive' 
                     : loopLimit.current >= loopLimit.max - 1 ? 'bg-amber-500' 
                     : 'bg-primary'
                  }`}
                  style={{ width: `${Math.min(100, (loopLimit.current / loopLimit.max) * 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Current: {loopLimit.current}</span>
                <span>Max: {loopLimit.max}</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === "architecture" && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Views</h3>
            <ul className="space-y-1">
              {[
                  { id: "c1", label: "C1 Context", icon: Boxes },
                  { id: "c2", label: "C2 Containers", icon: Database },
                  { id: "c3", label: "C3 Components", icon: Component },
                  { id: "c4", label: "C4 Code", icon: FileCode2 }
              ].map(view => {
                 const Icon = view.icon;
                 return (
                   <li
                     key={view.id}
                     className={`flex items-center gap-2 text-sm px-2 py-1.5 rounded cursor-pointer transition-colors ${archTab === view.id ? 'bg-secondary text-foreground' : 'text-foreground/80 hover:bg-secondary/50'}`}
                     onClick={() => setArchTab(view.id as typeof archTab)}
                   >
                     <Icon className="w-4 h-4 text-muted-foreground" />
                     {view.label}
                   </li>
                 );
              })}
            </ul>
          </div>
        )}
      </div>
    </aside>
  );
}
