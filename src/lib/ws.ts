import ReactUseWebSocket, { ReadyState } from "react-use-websocket";

const useWebSocket = ((ReactUseWebSocket as unknown as { default?: typeof ReactUseWebSocket }).default ?? ReactUseWebSocket);
import { useEffect } from "react";
import { useStore } from "./store";
import { IncomingFrame, OutgoingFrame } from "./protocol";

const WS_URL = "ws://localhost:8001/ws";

// Mount this exactly once (at the app root) so incoming frames are dispatched
// to the store a single time. Consumers that only need to send or read
// readyState should use `useMaestroSocket` instead.
export function MaestroSocketHost() {
  const handleIncoming = useStore((state) => state.handleIncoming);
  const { lastJsonMessage } = useWebSocket<IncomingFrame>(WS_URL, {
    shouldReconnect: () => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
    share: true,
  });

  useEffect(() => {
    if (lastJsonMessage) {
      handleIncoming(lastJsonMessage);
    }
  }, [lastJsonMessage, handleIncoming]);

  return null;
}

export function useMaestroSocket() {
  const { sendMessage, readyState } = useWebSocket<IncomingFrame>(WS_URL, {
    shouldReconnect: () => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
    share: true,
  });

  const send = (frame: OutgoingFrame) => {
    sendMessage(JSON.stringify(frame));
  };

  return {
    send,
    readyState,
    isConnected: readyState === ReadyState.OPEN,
  };
}
