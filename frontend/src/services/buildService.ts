import { api } from "./api";
import type { ProjectState } from "../types/project";
import type { ServerStatus } from "../types/generation";

export async function buildProject(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/build`);
  return data;
}

export async function startServer(projectId: string) {
  const { data } = await api.post<ServerStatus>(`/api/projects/${projectId}/start-server`);
  return data;
}

export async function stopServer(projectId: string) {
  const { data } = await api.post(`/api/projects/${projectId}/stop-server`);
  return data;
}

export async function getServerStatus(projectId: string) {
  const { data } = await api.get<ServerStatus>(`/api/projects/${projectId}/server-status`);
  return data;
}

