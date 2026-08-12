import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import type { ProjectState } from "../types/project";
import {
  generateCleanedSpec,
  generateRequirements,
  generateUserStories,
  generateArchitecture,
  generateDataModel,
  generateSrs,
  generatePostAnalysis,
} from "../services/workflowService";
import { api, getErrorMessage } from "../services/api";

export function useProjectMutation<TPayload>(
  projectId: string | undefined,
  mutationFn: (projectId: string, payload: TPayload) => Promise<ProjectState>,
  onSuccess?: (project: ProjectState) => void,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TPayload) => mutationFn(projectId!, payload),
    onSuccess: (project) => {
      queryClient.setQueryData(["project", project.project_id], project);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onSuccess?.(project);
    },
  });
}

export function useWorkflow(projectId: string) {
  const [generationError, setGenerationError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: logs } = useQuery({
    queryKey: ["logs", projectId],
    queryFn: async () => {
      if (!projectId) return [];
      try {
        const { data } = await api.get(`/api/projects/${projectId}/logs`);
        return data;
      } catch {
        return [];
      }
    },
    enabled: Boolean(projectId),
    refetchInterval: 2000, // Poll every 2 seconds during generation
  });

  const mutation = useMutation({
    mutationFn: async (stageName: string) => {
      setGenerationError(null);
      switch (stageName) {
        case "cleaned-spec":
          return await generateCleanedSpec(projectId);
        case "requirements":
          return await generateRequirements(projectId);
        case "user-stories":
          return await generateUserStories(projectId);
        case "architecture":
          return await generateArchitecture(projectId);
        case "data-model":
          return await generateDataModel(projectId);
        case "srs":
          return await generateSrs(projectId);
        case "post-analysis":
          return await generatePostAnalysis(projectId);
        case "code":
          const { data } = await api.post(`/api/projects/${projectId}/generate/code`, {}, { timeout: 0 });
          return data;
        default:
          throw new Error(`Unknown stage: ${stageName}`);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["project", projectId], data);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["logs", projectId] });
    },
    onError: (error: unknown) => {
      setGenerationError(getErrorMessage(error));
    },
  });

  return {
    generateStage: mutation.mutateAsync,
    isGenerating: mutation.isPending,
    generationError,
    logs: logs || [],
  };
}
