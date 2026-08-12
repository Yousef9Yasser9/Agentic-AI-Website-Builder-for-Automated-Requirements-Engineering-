import { api } from "./api";
import type { ProjectState } from "../types/project";

export async function generateCleanedSpec(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/cleaned-spec`, undefined, { timeout: 0 });
  return data;
}

export async function generateRequirements(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/requirements`, undefined, { timeout: 0 });
  return data;
}

export async function generateUserStories(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/user-stories`, undefined, { timeout: 0 });
  return data;
}

export async function generateArchitecture(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/architecture`, undefined, { timeout: 0 });
  return data;
}

export async function generateDataModel(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/data-model`, undefined, { timeout: 0 });
  return data;
}

export async function generateSrs(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/srs`, undefined, { timeout: 0 });
  return data;
}

export async function saveUiSelection(projectId: string, payload: Record<string, unknown>) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/ui-selection`, payload);
  return data;
}

export async function generatePostAnalysis(projectId: string) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/post-analysis`);
  return data;
}
