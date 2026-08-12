import axios from "axios";
import { getStoredToken } from "./authService";

/**
 * In local dev, leave VITE_API_URL empty so Vite proxies /api and /auth to the backend.
 * In production, set VITE_API_URL to the backend origin or leave empty when served from same host.
 */
const baseURL = import.meta.env.VITE_API_URL ?? "";

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
  // From-scratch local model generation can legitimately take a long time.
  timeout: 3600000,
});

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("ai_builder_token");
      window.dispatchEvent(new CustomEvent("auth:session-expired"));
    }
    return Promise.reject(error);
  },
);

type ValidationDetail = { msg?: string; loc?: (string | number)[] };

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
        return "Cannot connect to server. Make sure the backend is running on port 8000.";
      }
      if (error.code === "ECONNABORTED") {
        return "The local generation request exceeded the client wait time. The backend or Ollama may still be working.";
      }
      return error.message || "Unable to reach the backend server.";
    }

    const data = error.response.data as { detail?: string | ValidationDetail[] } | undefined;
    const detail = data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => item.msg || JSON.stringify(item))
        .filter(Boolean)
        .join(". ");
    }

    return error.message || `Request failed (${error.response.status}).`;
  }

  if (error instanceof Error) return error.message;
  return "Unexpected error";
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await api.get("/api/health", { timeout: 5000 });
    return response.status === 200;
  } catch {
    return false;
  }
}
