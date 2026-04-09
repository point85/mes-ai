import { useEffect, useRef, useState } from "react";
import type { MESEvent } from "../types";

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/v1/events/ws`;

type EventHandler = (event: MESEvent) => void;

export function useWebSocket(topics: string[], onEvent: EventHandler) {
  const [connected, setConnected] = useState(false);
  const handlersRef = useRef(onEvent);
  handlersRef.current = onEvent;
  const topicsRef = useRef(topics);
  topicsRef.current = topics;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    function connect() {
      if (disposed) return;
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (disposed) { ws?.close(); return; }
        setConnected(true);
        const t = topicsRef.current;
        if (t.length > 0) {
          ws!.send(JSON.stringify({ action: "subscribe", topics: t }));
        }
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.status === "pong" || data.status === "subscribed") return;
          handlersRef.current(data as MESEvent);
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!disposed) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => ws?.close();
    }

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []); // stable — never re-runs

  return { connected };
}
