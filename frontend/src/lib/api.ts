import axios from "axios";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (config.data instanceof FormData && config.headers) {
    delete (config.headers as Record<string, string>)["Content-Type"];
  }

  const access = localStorage.getItem("access_token");
  if (access) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

let isRefreshing = false;
let waiters: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = [];

const resolveWaiters = (token: string) => {
  waiters.forEach((w) => w.resolve(token));
  waiters = [];
};

const rejectWaiters = (err: unknown) => {
  waiters.forEach((w) => w.reject(err));
  waiters = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;
    const url = original?.url ?? "";

    if (!original) throw error;

    const isRefreshCall = url.includes("/users/refresh");

    if (status === 401 && !original._retry && !isRefreshCall) {
      original._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          waiters.push({
            resolve: (newAccess) => {
              original.headers = original.headers ?? {};
              original.headers.Authorization = `Bearer ${newAccess}`;
              resolve(api(original));
            },
            reject,
          });
        });
      }

      isRefreshing = true;
      try {
        const refresh = localStorage.getItem("refresh_token");
        if (!refresh) throw error;

        const r = await axios.post(`${BASE_URL}/users/refresh`, {
          refresh_token: refresh,
        });

        const newAccess = r.data?.access_token as string | undefined;
        const newRefresh = r.data?.refresh_token as string | undefined;

        if (!newAccess) throw error;

        localStorage.setItem("access_token", newAccess);
        if (newRefresh) localStorage.setItem("refresh_token", newRefresh);

        resolveWaiters(newAccess);

        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${newAccess}`;
        return api(original);
      } catch (e) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        rejectWaiters(e);
        throw e;
      } finally {
        isRefreshing = false;
      }
    }

    throw error;
  }
);