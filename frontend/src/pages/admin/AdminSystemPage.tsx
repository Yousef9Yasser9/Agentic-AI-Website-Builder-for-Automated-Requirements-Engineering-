import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cpu, HardDrive, RefreshCw, Server, Trash2 } from "lucide-react";
import { AdminLayout } from "../../components/layout/AdminLayout";
import { GlassCard } from "../../components/ui/GlassCard";
import { GradientButton } from "../../components/ui/GradientButton";
import { LoadingState } from "../../components/ui/LoadingState";
import { api } from "../../services/api";
import { fetchAdminSystemHealth } from "../../services/adminService";

export function AdminSystemPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["admin-system-health"],
    queryFn: fetchAdminSystemHealth,
    refetchInterval: 10000,
  });

  const cleanupMutation = useMutation({
    mutationFn: () => api.post("/api/system/cleanup", { keep_apps: 1, keep_checkpoints: 5 }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-system-health"] }),
  });

  if (isLoading) return <AdminLayout title="System Health"><LoadingState label="Loading system health..." /></AdminLayout>;

  const metrics = [
    { label: "CPU Usage", value: `${data?.cpu_percent ?? 0}%`, icon: Cpu },
    { label: "RAM Usage", value: `${data?.ram_percent ?? 0}%`, icon: Server },
    { label: "Disk Usage", value: `${data?.disk_percent ?? 0}%`, icon: HardDrive },
    { label: "Checkpoints", value: `${data?.checkpoints_size_mb ?? 0} MB`, icon: HardDrive },
    { label: "Generated Apps", value: `${data?.generated_apps_size_mb ?? 0} MB`, icon: HardDrive },
  ];

  return (
    <AdminLayout title="System Health" subtitle="Full infrastructure monitoring and cleanup">
      <div className="flex justify-end mb-4">
        <GradientButton onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </GradientButton>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <GlassCard key={metric.label} className="p-6">
              <div className="flex items-center gap-3">
                <Icon className="w-5 h-5 text-cyan-400" />
                <div>
                  <p className="text-sm text-slate-400">{metric.label}</p>
                  <p className="text-2xl font-bold text-white">{metric.value}</p>
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>

      <GlassCard className="p-6 mb-6">
        <h3 className="text-lg font-semibold text-white mb-3">Ollama</h3>
        <p className={data?.ollama?.online ? "text-emerald-400" : "text-red-400"}>
          {data?.ollama?.online ? "Online" : "Offline"}
        </p>
        {data?.warnings?.length > 0 && (
          <ul className="mt-4 space-y-2">
            {data.warnings.map((warning: string) => (
              <li key={warning} className="text-amber-300 text-sm">{warning}</li>
            ))}
          </ul>
        )}
      </GlassCard>

      <GlassCard className="p-6">
        <h3 className="text-lg font-semibold text-white mb-3">Cleanup Actions</h3>
        <p className="text-slate-400 text-sm mb-4">Prune old checkpoints and generated apps (keeps latest items).</p>
        <GradientButton onClick={() => cleanupMutation.mutate()} disabled={cleanupMutation.isPending}>
          <Trash2 className="w-4 h-4" />
          Run Cleanup
        </GradientButton>
      </GlassCard>
    </AdminLayout>
  );
}
