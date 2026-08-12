import { useQuery } from "@tanstack/react-query";
import { getOllamaStatus } from "../services/settingsService";

export function useOllamaStatus() {
  return useQuery({
    queryKey: ["ollama-status"],
    queryFn: getOllamaStatus,
    refetchInterval: 8000,
  });
}

