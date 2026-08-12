import { api } from "./api";
import type { ProjectState } from "../types/project";
import type { CodeGenerationOptions, LogsResponse } from "../types/generation";

export async function generateCode(projectId: string, options: CodeGenerationOptions) {
  const { data } = await api.post<ProjectState>(`/api/projects/${projectId}/generate/code`, options, {
    timeout: 0,
  });
  return data;
}

export async function getProjectLogs(projectId: string) {
  const { data } = await api.get<LogsResponse>(`/api/projects/${projectId}/logs`);
  return data;
}
