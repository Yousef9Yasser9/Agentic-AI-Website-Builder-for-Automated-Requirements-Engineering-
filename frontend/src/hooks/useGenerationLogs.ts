import { useQuery } from "@tanstack/react-query";
import { getProjectLogs } from "../services/generationService";

export function useGenerationLogs(projectId?: string, enabled = true) {
  return useQuery({
    queryKey: ["logs", projectId],
    queryFn: () => getProjectLogs(projectId!),
    enabled: Boolean(projectId) && enabled,
    refetchInterval: enabled ? 1800 : false,
  });
}

