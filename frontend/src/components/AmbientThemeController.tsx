import { useEffect } from "react";
import { useUIStore } from "../store/ui";

export default function AmbientThemeController() {
  const hydrate = useUIStore((s) => s.hydrate);
  const mode = useUIStore((s) => s.ambientMode);
  const manualTheme = useUIStore((s) => s.manualTheme);
  const lux = useUIStore((s) => s.lux);
  const setLux = useUIStore((s) => s.setLux);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    const theme = mode === "manual"
      ? manualTheme
      : lux <= 60
        ? "dim"
        : lux >= 320
          ? "bright"
          : "normal";

    document.documentElement.setAttribute("data-ambient", theme);
  }, [mode, manualTheme, lux]);

  useEffect(() => {
    if (mode !== "auto") return;

    const envWsUrl = import.meta.env.VITE_SENSOR_WS_URL as string | undefined;
    const apiUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
    const defaultWsUrl = `${apiUrl.replace("http://", "ws://").replace("https://", "wss://")}/ws/ambient`;
    const wsUrl = envWsUrl && envWsUrl.trim().length > 0 ? envWsUrl : defaultWsUrl;

    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let attempt = 0;
    let isClosedByClient = false;

    const connect = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        attempt = 0;
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as { lux?: number };
          if (typeof payload.lux === "number") {
            setLux(payload.lux);
          }
        } catch {
          // Ignore malformed sensor payloads.
        }
      };

      ws.onclose = () => {
        if (isClosedByClient) return;
        const backoff = Math.min(15000, 1000 * 2 ** attempt);
        reconnectTimer = window.setTimeout(() => {
          attempt += 1;
          connect();
        }, backoff);
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      isClosedByClient = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    };
  }, [mode, setLux]);

  return null;
}
