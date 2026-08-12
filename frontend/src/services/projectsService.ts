import { api } from "./api";
import type { ProjectState, ProjectSummary, StageKey } from "../types/project";

export async function listProjects() {
  const { data } = await api.get<ProjectSummary[]>("/api/projects");
  return data;
}

export async function createProject(plain_text?: string) {
  const { data } = await api.post<ProjectState>("/api/projects", { plain_text });
  return data;
}

export async function getProject(projectId: string) {
  const { data } = await api.get<ProjectState>(`/api/projects/${projectId}`);
  return data;
}

export async function deleteProject(projectId: string) {
  const { data } = await api.delete(`/api/projects/${projectId}`);
  return data;
}

export async function updatePlainText(projectId: string, plain_text: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/plain-text`, { plain_text });
  return data;
}

export async function updateProjectStage(projectId: string, stage: StageKey) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/stage`, { stage });
  return data;
}

export function artifactUrl(projectId: string, artifactName: string) {
  return `/api/projects/${projectId}/artifact/${artifactName}`;
}

