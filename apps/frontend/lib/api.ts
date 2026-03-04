import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
});

// Attach JWT token from localStorage to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const res = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("access_token", res.data.access_token);
          localStorage.setItem("refresh_token", res.data.refresh_token);
          original.headers.Authorization = `Bearer ${res.data.access_token}`;
          return api(original);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post("/auth/register", data),
  login: (data: { email: string; password: string }) =>
    api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
  createApiKey: (name?: string) =>
    api.post(`/auth/api-keys${name ? `?name=${name}` : ""}`),
};

// Signals
export const signalsApi = {
  recent: (minutes = 60, symbol?: string) =>
    api.get("/signals/recent", { params: { minutes, symbol } }),
  byId: (id: string) => api.get(`/signals/${id}`),
};

// Trades
export const tradesApi = {
  open: (accountId: string) =>
    api.get("/trades/open", { params: { account_id: accountId } }),
  history: (accountId: string, limit = 50, offset = 0) =>
    api.get("/trades/history", { params: { account_id: accountId, limit, offset } }),
};

// Accounts
export const accountsApi = {
  list: () => api.get("/accounts/"),
  link: (data: { broker_name: string; account_number: string; server_name: string; leverage: number; risk_profile: string }) =>
    api.post("/accounts/link", data),
  liveData: (accountId: string) => api.get(`/accounts/${accountId}/live`),
};

// Risk
export const riskApi = {
  killSwitch: (accountId: string) =>
    api.get(`/risk/kill-switch/${accountId}`),
  events: (accountId: string, limit = 20) =>
    api.get(`/risk/events/${accountId}`, { params: { limit } }),
  performance: (accountId: string, limit = 30) =>
    api.get(`/risk/performance/${accountId}`, { params: { limit } }),
};

// Subscriptions
export const subscriptionApi = {
  plans: () => api.get("/subscriptions/plans"),
  mine: () => api.get("/subscriptions/me"),
};
