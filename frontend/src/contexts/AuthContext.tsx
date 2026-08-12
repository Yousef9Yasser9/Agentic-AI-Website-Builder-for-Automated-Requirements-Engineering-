import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as authService from "../services/authService";
import { getErrorMessage } from "../services/api";
import type { AuthMessageResponse, AuthUser } from "../types/auth";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  register: (full_name: string, email: string, password: string) => Promise<AuthMessageResponse>;
  verifyOtp: (email: string, otp: string, purpose?: "register_verification" | "password_reset") => Promise<AuthUser | void>;
  resendOtp: (email: string, purpose?: "register_verification" | "password_reset") => Promise<AuthMessageResponse>;
  forgotPassword: (email: string) => Promise<string>;
  resetPassword: (email: string, otp: string, new_password: string) => Promise<string>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    const token = authService.getStoredToken();
    if (!token) {
      setUser(null);
      return;
    }
    const me = await authService.fetchMe();
    setUser(me);
  }, []);

  useEffect(() => {
    refreshUser()
      .catch(() => {
        authService.setStoredToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [refreshUser]);

  useEffect(() => {
    const handleExpiredSession = () => {
      setUser(null);
      setError("Your session expired. Please sign in again.");
    };
    window.addEventListener("auth:session-expired", handleExpiredSession);
    return () => window.removeEventListener("auth:session-expired", handleExpiredSession);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const data = await authService.login(email, password);
      authService.setStoredToken(data.access_token);
      const loggedInUser = data.user ?? await authService.fetchMe();
      setUser(loggedInUser);
      return loggedInUser;
    } catch (err) {
      authService.setStoredToken(null);
      const message = getErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  const register = useCallback(async (full_name: string, email: string, password: string) => {
    setError(null);
    try {
      const data = await authService.register(full_name, email, password);
      return data;
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }, []);

  const verifyOtp = useCallback(async (email: string, otp: string, purpose: "register_verification" | "password_reset" = "register_verification") => {
    setError(null);
    try {
      const data = await authService.verifyOtp(email, otp, purpose);
      if ("access_token" in data) {
        authService.setStoredToken(data.access_token);
        const verifiedUser = data.user ?? await authService.fetchMe();
        setUser(verifiedUser);
        return verifiedUser;
      }
    } catch (err) {
      authService.setStoredToken(null);
      const message = getErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }, []);

  const resendOtp = useCallback(async (email: string, purpose: "register_verification" | "password_reset" = "register_verification") => {
    setError(null);
    try {
      const data = await authService.resendOtp(email, purpose);
      return data;
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    setError(null);
    try {
      const data = await authService.forgotPassword(email);
      return data.message;
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }, []);

  const resetPassword = useCallback(async (email: string, otp: string, new_password: string) => {
    setError(null);
    try {
      const data = await authService.resetPassword(email, otp, new_password);
      return data.message;
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      isAuthenticated: !!user,
      isAdmin: user?.role === "admin",
      login,
      logout,
      register,
      verifyOtp,
      resendOtp,
      forgotPassword,
      resetPassword,
      refreshUser,
      clearError: () => setError(null),
    }),
    [user, loading, error, login, logout, register, verifyOtp, resendOtp, forgotPassword, resetPassword, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
