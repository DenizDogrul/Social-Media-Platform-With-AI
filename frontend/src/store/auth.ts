import { create } from "zustand";
import { api } from "../lib/api";
import { useUIStore } from "./ui";

type CurrentUser = {
  id: number;
  username: string;
  email: string;
  is_verified?: boolean;
  is_admin?: boolean;
};

type AuthState = {
  isAuthenticated: boolean;
  user: CurrentUser | null;
  isHydrated: boolean;
  hydrate: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  user: null,
  isHydrated: false,

  hydrate: async () => {
    try {
      const access = localStorage.getItem("access_token");
      if (!access) {
        set({ isAuthenticated: false, user: null, isHydrated: true });
        return;
      }

      set({ isAuthenticated: true });
      try {
        const me = await api.get<CurrentUser>("/users/me");
        set({ user: me.data, isAuthenticated: true, isHydrated: true });
      } catch (err) {
        console.error("Hydration: /users/me failed", err);
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ isAuthenticated: false, user: null, isHydrated: true });
      }
    } catch (err) {
      console.error("Hydration error:", err);
      set({ isAuthenticated: false, user: null, isHydrated: true });
    }
  },

  login: async (username, password) => {
    const r = await api.post("/users/login", { username, password });
    localStorage.setItem("access_token", r.data.access_token);
    localStorage.setItem("refresh_token", r.data.refresh_token);
    const me = await api.get<CurrentUser>("/users/me");
    set({ isAuthenticated: true, user: me.data });
  },

  register: async (username, email, password) => {
    await api.post("/users/register", { username, email, password });
    await get().login(username, password);
  },

  logout: async () => {
    try {
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) await api.post("/users/logout", { refresh_token: refresh });
    } catch {}
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    
    // Clear UI state (notifications, etc.)
    useUIStore.setState({ notificationItems: [], notifications: 0 });
    
    set({ isAuthenticated: false, user: null, isHydrated: true });
  },
}));