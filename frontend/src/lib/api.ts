import axios, {
  type AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

import { useAuthStore } from "@/stores/auth";
import { API_URL } from "@/lib/utils";

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
});

// ---- Request interceptor: Bearer access token ----
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---- Response interceptor: 401 → refresh va navbatga olish ----
let isRefreshing = false;
let pending: Array<(token: string | null) => void> = [];

function flushQueue(token: string | null) {
  pending.forEach((cb) => cb(token));
  pending = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    if (
      !original ||
      error.response?.status !== 401 ||
      original._retry ||
      original.url?.includes("/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    const { refreshToken, setTokens, logout } = useAuthStore.getState();
    if (!refreshToken) {
      logout();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pending.push((token) => {
          if (!token) {
            reject(error);
            return;
          }
          original.headers.Authorization = `Bearer ${token}`;
          original._retry = true;
          resolve(api(original));
        });
      });
    }

    original._retry = true;
    isRefreshing = true;
    try {
      const resp = await axios.post(
        `${API_URL}/auth/refresh`,
        { refresh_token: refreshToken },
        { timeout: 10000 },
      );
      const access = resp.data.access_token as string;
      const refresh = resp.data.refresh_token as string;
      setTokens(access, refresh);
      flushQueue(access);
      original.headers.Authorization = `Bearer ${access}`;
      return api(original);
    } catch (refreshErr) {
      flushQueue(null);
      logout();
      return Promise.reject(refreshErr);
    } finally {
      isRefreshing = false;
    }
  },
);

// ---- DX helper ----
export async function getJson<T>(url: string, config?: AxiosRequestConfig) {
  const r = await api.get<T>(url, config);
  return r.data;
}
