import { Cpu, WifiOff } from "lucide-react";
import type { OllamaStatus } from "../../types/project";
import { StatusBadge } from "../ui/StatusBadge";

export function OllamaStatusBadge({ status }: { status?: OllamaStatus }) {
  if (!status) return <StatusBadge tone="pending">Checking Ollama</StatusBadge>;
  if (!status.online) {
    return (
      <StatusBadge tone="error">
        <WifiOff className="h-3.5 w-3.5" />
        Offline
      </StatusBadge>
    );
  }
  return (
    <StatusBadge tone={status.ram_warning ? "warning" : "success"}>
      <Cpu className="h-3.5 w-3.5" />
      {status.ram_warning ? `High RAM ${Math.round(status.ram_percent || 0)}%` : "Ollama Online"}
    </StatusBadge>
  );
}

