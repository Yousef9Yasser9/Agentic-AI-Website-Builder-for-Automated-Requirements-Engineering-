import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Save, Zap } from "lucide-react";
import { AdminLayout } from "../../components/layout/AdminLayout";
import { ModelSettingsPanel } from "../../components/settings/ModelSettingsPanel";
import { OllamaStatusBadge } from "../../components/settings/OllamaStatusBadge";
import { GlassCard } from "../../components/ui/GlassCard";
import { GradientButton } from "../../components/ui/GradientButton";
import { testModelConnection } from "../../services/adminService";
import { api } from "../../services/api";

export function AdminModelsPage() {
  const queryClient = useQueryClient();
  const { data: ollama } = useQuery({
    queryKey: ["ollama-status"],
    queryFn: async () => (await api.get("/api/ollama/status")).data,
    refetchInterval: 10000,
  });

  const testMutation = useMutation({
    mutationFn: testModelConnection,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ollama-status"] }),
  });

  return (
    <AdminLayout title="Model Management" subtitle="Configure architect/coder models for the AI builder pipeline">
      <div className="grid lg:grid-cols-3 gap-6">
        <GlassCard className="p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Model Settings</h3>
            <OllamaStatusBadge />
          </div>
          <ModelSettingsPanel />
        </GlassCard>

        <div className="space-y-6">
          <GlassCard className="p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Available Ollama Models</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {(ollama?.models || []).map((model: string) => (
                <div key={model} className="px-3 py-2 rounded-lg bg-white/5 text-sm text-slate-300 font-mono">
                  {model}
                </div>
              ))}
              {!ollama?.models?.length && <p className="text-slate-500 text-sm">No models loaded or Ollama offline.</p>}
            </div>
            <GradientButton
              className="w-full mt-4 justify-center"
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
            >
              {testMutation.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              Test Connection
            </GradientButton>
          </GlassCard>

          <GlassCard className="p-6">
            <h3 className="text-lg font-semibold text-white mb-2">Persistence</h3>
            <p className="text-slate-400 text-sm">
              Saved model settings are stored in <code className="text-cyan-300">.tmp/model_settings.json</code> and used by future builder generation tasks.
            </p>
            <div className="mt-4 flex items-center gap-2 text-emerald-400 text-sm">
              <Save className="w-4 h-4" /> Changes apply to new generations immediately
            </div>
          </GlassCard>
        </div>
      </div>
    </AdminLayout>
  );
}
