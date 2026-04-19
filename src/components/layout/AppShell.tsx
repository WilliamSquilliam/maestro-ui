import { useState } from "react";
import { TopBar } from "./TopBar";
import { LeftNav } from "./LeftNav";
import { ChatView } from "../chat/ChatView";
import { ArchitectureView } from "../diagram/ArchitectureView";

export function AppShell() {
  const [activeTab, setActiveTab] = useState<"chat" | "architecture">("chat");

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <LeftNav activeTab={activeTab} setActiveTab={setActiveTab} />
        
        <main className="flex-1 overflow-hidden relative">
          {activeTab === "chat" ? <ChatView /> : <ArchitectureView />}
        </main>
      </div>
    </div>
  );
}
