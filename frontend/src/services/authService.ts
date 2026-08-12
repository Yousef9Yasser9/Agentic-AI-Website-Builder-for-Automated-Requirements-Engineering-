import { api } from "./api";
import type { AuthMessageResponse, AuthTokenResponse, AuthUser } from "../types/auth";

const TOKEN_KEY = "access_token";
const LEGACY_TOKEN_KEY = "ai_builder_token";

export function getStoredToken(): string | null {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) return token;
  const legacyToken = localStorage.getItem(LEGACY_TOKEN_KEY);
  if (legacyToken) {
    localStorage.setItem(TOKEN_KEY, legacyToken);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
  }
  return legacyToken;
}

export function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
  }
}

export async function register(full_name: string, email: string, password: string) {
  const response = await api.post("/auth/register", { full_name, email, password });
  return response.data as AuthMessageResponse;
}

export async function verifyOtp(email: string, otp: string, purpose: "register_verification" | "password_reset") {
  const response = await api.post("/auth/verify-otp", { email, otp, purpose });
  return response.data as AuthTokenResponse | { message: string };
}

export async function resendOtp(email: string, purpose: "register_verification" | "password_reset") {
  const response = await api.post("/auth/resend-otp", { email, purpose });
  return response.data as AuthMessageResponse;
}

export async function login(email: string, password: string) {
  const response = await api.post<AuthTokenResponse>("/auth/login", { email, password });
  return response.data;
}

export async function logout() {
  try {
    await api.post("/auth/logout");
  } finally {
    setStoredToken(null);
  }
}

export async function fetchMe(): Promise<AuthUser> {
  const response = await api.get<AuthUser>("/auth/me");
  return response.data;
}

export async function forgotPassword(email: string) {
  const response = await api.post("/auth/forgot-password", { email });
  return response.data as { message: string };
}

export async function resetPassword(email: string, otp: string, new_password: string) {
  const response = await api.post("/auth/reset-password", { email, otp, new_password });
  return response.data as { message: string };
}
