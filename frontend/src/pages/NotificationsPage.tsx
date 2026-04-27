import { useEffect, useState } from "react";
import { useUIStore } from "../store/ui";
import { api } from "../lib/api";

export function NotificationsPage() {
  const notificationItems = useUIStore((s) => s.notificationItems);
  const setNotificationItems = useUIStore((s) => s.setNotificationItems);
  const markNotificationRead = useUIStore((s) => s.markNotificationRead);
  const markAllNotificationsRead = useUIStore((s) => s.markAllNotificationsRead);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Load all notifications on mount
  useEffect(() => {
    const loadNotifications = async () => {
      try {
        setLoading(true);
        const res = await api.get("/notifications");
        setNotificationItems(res.data);
      } catch (err: any) {
        console.error("Failed to load notifications:", err);
        setError("Failed to load notifications");
      } finally {
        setLoading(false);
      }
    };

    loadNotifications();
  }, [setNotificationItems]);

  const onMarkRead = async (notificationId: number) => {
    try {
      await api.post(`/notifications/${notificationId}/read`);
      markNotificationRead(notificationId);
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  };

  const onMarkAllRead = async () => {
    try {
      await api.post("/notifications/read-all");
      markAllNotificationsRead();
    } catch (err) {
      console.error("Failed to mark all notifications as read:", err);
    }
  };

  const unreadCount = notificationItems.filter((n) => !n.is_read).length;

  return (
    <section className="social-grid single-col">
      <section className="feed-layout">
        <section className="card post-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2>Notifications</h2>
            {unreadCount > 0 && (
              <button className="btn-ghost" onClick={() => void onMarkAllRead()}>
                Mark all read ({unreadCount})
              </button>
            )}
          </div>

          {loading && <p className="meta">Loading notifications...</p>}

          {error && <p style={{ color: "var(--error, #d32f2f)" }}>{error}</p>}

          {!loading && notificationItems.length === 0 && (
            <p className="meta">No notifications yet.</p>
          )}

          {!loading && notificationItems.length > 0 && (
            <div className="notification-list">
              {notificationItems.map((n) => (
                <button
                  key={n.id}
                  className={`notification-item notification-button ${n.is_read ? "" : "notification-unread"}`}
                  onClick={() => void onMarkRead(n.id)}
                >
                  <strong>{n.title}</strong>
                  <span>{n.body}</span>
                  {n.created_at && (
                    <span className="meta">
                      {new Date(n.created_at).toLocaleDateString()} {new Date(n.created_at).toLocaleTimeString()}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </section>
      </section>
    </section>
  );
}
