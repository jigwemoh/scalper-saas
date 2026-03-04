"use client";

import { useEffect, useRef, useCallback } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

type WSMessage = {
  type: "account_update" | "positions_update" | "signal" | "kill_switch";
  data: unknown;
};

type Handler = (message: WSMessage) => void;

let ws: WebSocket | null = null;
const handlers = new Set<Handler>();
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log("WS connected");
    if (reconnectTimer) clearTimeout(reconnectTimer);
  };

  ws.onmessage = (event) => {
    try {
      const msg: WSMessage = JSON.parse(event.data);
      handlers.forEach((h) => h(msg));
    } catch {}
  };

  ws.onclose = () => {
    console.log("WS disconnected — reconnecting in 3s");
    reconnectTimer = setTimeout(connect, 3000);
  };

  ws.onerror = () => ws?.close();
}

export function useWebSocket(onMessage: Handler) {
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  const stableHandler = useCallback((msg: WSMessage) => {
    handlerRef.current(msg);
  }, []);

  useEffect(() => {
    connect();
    handlers.add(stableHandler);
    return () => {
      handlers.delete(stableHandler);
    };
  }, [stableHandler]);
}
