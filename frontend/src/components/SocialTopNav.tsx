import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { useUIStore } from "../store/ui";
import VerificationBadge from "./VerificationBadge";

type SocialTopNavProps = {
  title: string;
  subtitle?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
};

const urlBase64ToUint8Array = (base64String: string) => {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
};

export default function SocialTopNav({ title, subtitle, searchValue, onSearchChange }: SocialTopNavProps) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const notifications = useUIStore((s) => s.notifications);
  const notificationItems = useUIStore((s) => s.notificationItems);
  const mode = useUIStore((s) => s.ambientMode);
  const manualTheme = useUIStore((s) => s.manualTheme);
  const lux = useUIStore((s) => s.lux);
  const setMode = useUIStore((s) => s.setAmbientMode);
  const setManualTheme = useUIStore((s) => s.setManualTheme);
  const setNotificationItems = useUIStore((s) => s.setNotificationItems);
  const addNotification = useUIStore((s) => s.addNotification);
  const markNotificationRead = useUIStore((s) => s.markNotificationRead);
  const markAllNotificationsRead = useUIStore((s) => s.markAllNotificationsRead);
  const [dmUnread, setDmUnread] = useState(0);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [browserPermission, setBrowserPermission] = useState<NotificationPermission | "unsupported">(
    typeof window !== "undefined" && "Notification" in window ? Notification.permission : "unsupported",
  );

  const unreadNotifications = useMemo(
    () => notificationItems.filter((item) => !item.is_read).length,
    [notificationItems],
  );

  useEffect(() => {
    const loadNotifications = async () => {
      try {
        const response = await api.get<Array<{ id: number; title: string; body: string; is_read: boolean; created_at: string | null }>>("/notifications");
        setNotificationItems(response.data);
      } catch {
        // Keep UI resilient when notifications endpoint is unavailable.
      }
    };

    void loadNotifications();
  }, [setNotificationItems]);

  useEffect(() => {
    const setupPushSubscription = async () => {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        return;
      }

      try {
        const configRes = await api.get<{ enabled: boolean; public_key: string }>("/notifications/push-config");
        if (!configRes.data.enabled || !configRes.data.public_key) {
          return;
        }

        const registration = await navigator.serviceWorker.register("/sw.js");
        const existing = await registration.pushManager.getSubscription();
        const subscription = existing
          ?? await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(configRes.data.public_key),
          });

        const payload = subscription.toJSON() as {
          endpoint?: string;
          keys?: { p256dh?: string; auth?: string };
        };
        if (!payload.endpoint || !payload.keys?.p256dh || !payload.keys?.auth) {
          return;
        }

        await api.post("/notifications/push-subscriptions", {
          endpoint: payload.endpoint,
          keys: {
            p256dh: payload.keys.p256dh,
            auth: payload.keys.auth,
          },
        });
      } catch {
        // Push setup should not block main UI.
      }
    };

    void setupPushSubscription();
  }, []);

  useEffect(() => {
    const loadUnread = async () => {
      try {
        const response = await api.get<{ unread_count: number }>("/messages/unread-count");
        setDmUnread(response.data.unread_count ?? 0);
      } catch {
        setDmUnread(0);
      }
    };

    void loadUnread();
    const timer = window.setInterval(() => {
      void loadUnread();
    }, 20000);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const isAuth = useAuthStore.getState().isAuthenticated;
    if (!token || !isAuth) {
      // User not authenticated - don't connect
      return;
    }

    const apiUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
    const wsUrl = apiUrl.replace("http://", "ws://").replace("https://", "wss://");
    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let heartbeatTimer: number | null = null;
    let attempt = 0;
    let isClosedByClient = false;

    const clearTimers = () => {
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (heartbeatTimer !== null) {
        window.clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    };

    const scheduleReconnect = () => {
      if (isClosedByClient) return;
      const backoff = Math.min(30000, 1000 * 2 ** attempt);
      reconnectTimer = window.setTimeout(() => {
        attempt += 1;
        connect();
      }, backoff);
    };

    const connect = () => {
      clearTimers();
      ws = new WebSocket(`${wsUrl}/ws/notifications?token=${encodeURIComponent(token)}`);

      ws.onopen = () => {
        attempt = 0;
        heartbeatTimer = window.setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as { type?: string; notification?: { id: number; title: string; body: string; is_read: boolean; created_at: string | null } };
          if (payload.type === "notification" && payload.notification) {
            addNotification(payload.notification);
            if (
              typeof window !== "undefined"
              && "Notification" in window
              && Notification.permission === "granted"
              && document.visibilityState !== "visible"
            ) {
              new Notification(payload.notification.title, { body: payload.notification.body });
            }
          }
        } catch {
          // Ignore malformed messages.
        }
      };

      ws.onclose = () => {
        clearTimers();
        scheduleReconnect();
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      isClosedByClient = true;
      clearTimers();
      ws?.close();
    };
  }, [user?.id, addNotification]); // Reconnect when user changes (login/logout)

  const onMarkAllRead = async () => {
    markAllNotificationsRead();
    try {
      await api.post("/notifications/read-all");
    } catch {
      // Local optimistic state is sufficient for now.
    }
  };

  const onMarkRead = async (notificationId: number) => {
    markNotificationRead(notificationId);
    try {
      await api.post(`/notifications/${notificationId}/read`);
    } catch {
      // Local optimistic state is sufficient for now.
    }
  };

  const requestBrowserPermission = async () => {
    if (!("Notification" in window)) {
      setBrowserPermission("unsupported");
      return;
    }
    const permission = await Notification.requestPermission();
    setBrowserPermission(permission);
  };

  return (
    <header className="card topbar social-nav social-nav-clean">
      <div>
        <p className="brand">Nebula</p>
        <h1>{title}</h1>
        {subtitle && <p className="meta">{subtitle}</p>}
      </div>

      <div className="nav-controls">
        {onSearchChange && (
          <input
            className="search-input"
            value={searchValue ?? ""}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key !== "Enter") {
                return;
              }
              const query = e.currentTarget.value.trim();
              if (!query) {
                return;
              }
              navigate(`/search?q=${encodeURIComponent(query)}`);
            }}
            placeholder="Filter feed (Enter = global user search)"
          />
        )}

        <div className="nav-main-row">
          <Link className="nav-link" to="/notifications">Notifications <span className="notif-pill">{unreadNotifications || notifications}</span></Link>
          <button className="bell-button" onClick={() => setIsNotificationOpen((open) => !open)}>
            Quick view
            <span className="notif-pill">{unreadNotifications || notifications}</span>
          </button>
          <Link className="nav-link" to="/messages">DM {dmUnread}</Link>
          {(unreadNotifications > 0 || notifications > 0) && (
            <button className="btn-ghost" onClick={() => void onMarkAllRead()}>Mark all read</button>
          )}
          {user && <span className="meta nav-user-chip">@{user.username}<VerificationBadge verified={user.is_verified} compact /></span>}
        </div>

        <div className="nav-links-row">
          <Link className="nav-link" to="/search">Search</Link>
          <Link className="nav-link" to="/stories">Stories</Link>
          <Link className="nav-link" to="/saved">Saved</Link>
          <Link className="nav-link" to="/profile">My Profile</Link>
          {user?.is_admin && <Link className="nav-link" to="/admin">Admin</Link>}
          {browserPermission !== "unsupported" && browserPermission !== "granted" && (
            <button className="btn-ghost" onClick={() => void requestBrowserPermission()}>Enable browser alerts</button>
          )}
        </div>

        {isNotificationOpen && (
          <div className="notification-panel">
            {notificationItems.length === 0 && <p className="meta">No notifications yet.</p>}
            {notificationItems.slice(0, 8).map((n) => (
              <button
                key={n.id}
                className={`notification-item notification-button ${n.is_read ? "" : "notification-unread"}`}
                onClick={() => void onMarkRead(n.id)}
              >
                <strong>{n.title}</strong>
                <span>{n.body}</span>
              </button>
            ))}
          </div>
        )}

        <div className="row ambient-row">
          <label className="meta">Ambient</label>
          <select value={mode} onChange={(e) => setMode(e.target.value === "manual" ? "manual" : "auto")}> 
            <option value="auto">Auto</option>
            <option value="manual">Manual</option>
          </select>

          {mode === "manual" ? (
            <select value={manualTheme} onChange={(e) => setManualTheme(e.target.value as "dim" | "normal" | "bright")}> 
              <option value="dim">Dim</option>
              <option value="normal">Normal</option>
              <option value="bright">Bright</option>
            </select>
          ) : (
            <span className="meta">Live {lux} lx</span>
          )}
        </div>
      </div>
    </header>
  );
}
