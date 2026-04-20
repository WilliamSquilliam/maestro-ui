import ReactUseWebSocket, { ReadyState } from "react-use-websocket";

const useWebSocket = ((ReactUseWebSocket as unknown as { default?: typeof ReactUseWebSocket }).default ?? ReactUseWebSocket);
import { useEffect } from "react";
import { useStore } from "./store";
import { IncomingFrame, OutgoingFrame } from "./protocol";

const WS_URL = "ws://localhost:8001/ws";

export function useMaestroSocket() {
  const handleIncoming = useStore((state) => state.handleIncoming);

  const { sendMessage, lastJsonMessage, readyState } = useWebSocket<IncomingFrame>(
    WS_URL,
    {
      shouldReconnect: () => true,
      reconnectAttempts: 10,
      reconnectInterval: 3000,
      share: true,
    }
  );

  useEffect(() => {
    if (lastJsonMessage) {
      handleIncoming(lastJsonMessage);
    }
  }, [lastJsonMessage, handleIncoming]);

  const send = (frame: OutgoingFrame) => {
    sendMessage(JSON.stringify(frame));
  };

  return {
    send,
    readyState,
    isConnected: readyState === ReadyState.OPEN,
  };
}
