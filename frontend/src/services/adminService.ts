import { api } from "./api";
import type { AuthUser } from "../types/auth";

export interface AdminStats {
  total_users: number;
  verified_users: number;
  disabled_users: number;
  total_projects: number;
  total_generated_apps: number;
  active_running_apps: number;
  ollama_online: boolean;
  recent_users: AuthUser[];
  recent_projects: AdminProject[];
  system_warnings: string[];
}

export interface AdminProject {
  project_id: string;
  project_title: string;
  stage: string;
  saved_at?: string;
  owner_user_id?: number | null;
  completion_percent?: number;
  generated_app_status?: string;
}

export interface AdminGeneratedApp {
  project_id: string;
  app_name: string;
  owner_user_id?: number | null;
  stack: string | Record<string, unknown>;
  folder_path?: string;
  server_port?: number;
  running: boolean;
}

export interface AdminLogEntry {
  project_id: string;
  message: string;
}

export interface AdminLogsResponse {
  logs: AdminLogEntry[];
}

export async function fetchAdminStats() {
  const response = await api.get<AdminStats>("/api/admin/stats");
  return response.data;
}

export async function fetchAdminUsers() {
  const response = await api.get<AuthUser[]>("/api/admin/users");
  return response.data;
}

export async function updateAdminUser(userId: number, payload: { is_active?: boolean; role?: "user" | "admin" }) {
  const response = await api.patch<AuthUser>(`/api/admin/users/${userId}`, payload);
  return response.data;
}

export async function fetchAdminProjects() {
  const response = await api.get<AdminProject[]>("/api/admin/projects");
  return response.data;
}

export async function fetchAdminGeneratedApps() {
  const response = await api.get<AdminGeneratedApp[]>("/api/admin/generated-apps");
  return response.data;
}

export async function fetchAdminSystemHealth() {
  const response = await api.get("/api/admin/system/health");
  return response.data;
}

export async function fetchAdminLogs() {
  const response = await api.get<AdminLogsResponse>("/api/admin/logs");
  return response.data;
}

export async function testModelConnection() {
  const response = await api.post("/api/admin/models/test");
  return response.data;
}
