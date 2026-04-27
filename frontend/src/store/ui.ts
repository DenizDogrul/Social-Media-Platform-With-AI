import { create } from "zustand";

type AmbientMode = "auto" | "manual";
type AmbientTheme = "dim" | "normal" | "bright";

type UIState = {
  ambientMode: AmbientMode;
  manualTheme: AmbientTheme;
  lux: number;
  notifications: number;
  notificationItems: Array<{ id: number; title: string; body: string; is_read: boolean; created_at: string | null }>;
  hydrate: () => void;
  setAmbientMode: (mode: AmbientMode) => void;
  setManualTheme: (theme: AmbientTheme) => void;
  setLux: (lux: number) => void;
  setNotifications: (count: number) => void;
  setNotificationItems: (items: Array<{ id: number; title: string; body: string; is_read: boolean; created_at: string | null }>) => void;
  addNotification: (item: { id: number; title: string; body: string; is_read: boolean; created_at: string | null }) => void;
  markNotificationRead: (id: number) => void;
  markAllNotificationsRead: () => void;
  resolvedTheme: () => AmbientTheme;
};

const keyMode = "ambient_mode";
const keyTheme = "ambient_manual_theme";
const keyLux = "ambient_lux";

const resolveAmbientTheme = (mode: AmbientMode, manualTheme: AmbientTheme, lux: number): AmbientTheme => {
  if (mode === "manual") return manualTheme;
  if (lux <= 60) return "dim";
  if (lux >= 320) return "bright";
  return "normal";
};

export const useUIStore = create<UIState>((set, get) => ({
  ambientMode: "auto",
  manualTheme: "normal",
  lux: 160,
  notifications: 3,
  notificationItems: [],

  hydrate: () => {
    const storedMode = localStorage.getItem(keyMode);
    const storedTheme = localStorage.getItem(keyTheme);
    const storedLux = localStorage.getItem(keyLux);

    const nextMode = storedMode === "manual" ? "manual" : "auto";
    const nextTheme = storedTheme === "dim" || storedTheme === "bright" || storedTheme === "normal"
      ? storedTheme
      : "normal";
    const parsedLux = Number(storedLux);
    const nextLux = Number.isFinite(parsedLux) ? Math.min(1000, Math.max(0, parsedLux)) : 160;

    set({ ambientMode: nextMode, manualTheme: nextTheme, lux: nextLux });
  },

  setAmbientMode: (mode) => {
    localStorage.setItem(keyMode, mode);
    set({ ambientMode: mode });
  },

  setManualTheme: (theme) => {
    localStorage.setItem(keyTheme, theme);
    set({ manualTheme: theme });
  },

  setLux: (lux) => {
    const next = Math.min(1000, Math.max(0, lux));
    localStorage.setItem(keyLux, String(next));
    set({ lux: next });
  },

  setNotifications: (count) => {
    set({ notifications: Math.max(0, count) });
  },

  setNotificationItems: (items) => {
    const unread = items.filter((n) => !n.is_read).length;
    set({ notificationItems: items, notifications: unread });
  },

  addNotification: (item) => {
    set((state) => ({
      notificationItems: [item, ...state.notificationItems].slice(0, 30),
      notifications: state.notifications + (item.is_read ? 0 : 1),
    }));
  },

  markNotificationRead: (id) => {
    set((state) => {
      const notificationItems = state.notificationItems.map((item) =>
        item.id === id ? { ...item, is_read: true } : item,
      );
      return {
        notificationItems,
        notifications: notificationItems.filter((item) => !item.is_read).length,
      };
    });
  },

  markAllNotificationsRead: () => {
    set((state) => ({
      notificationItems: state.notificationItems.map((item) => ({ ...item, is_read: true })),
      notifications: 0,
    }));
  },

  resolvedTheme: () => {
    const { ambientMode, manualTheme, lux } = get();
    return resolveAmbientTheme(ambientMode, manualTheme, lux);
  },
}));
