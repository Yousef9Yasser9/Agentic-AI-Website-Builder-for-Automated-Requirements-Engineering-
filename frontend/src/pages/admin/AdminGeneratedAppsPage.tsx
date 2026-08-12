import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { AdminLayout } from "../../components/layout/AdminLayout";
import { GlassCard } from "../../components/ui/GlassCard";
import { LoadingState } from "../../components/ui/LoadingState";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { api } from "../../services/api";
import { fetchAdminGeneratedApps } from "../../services/adminService";

export function AdminGeneratedAppsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin-generated-apps"], queryFn: fetchAdminGeneratedApps });

  const stopMutation = useMutation({
    mutationFn: (projectId: string) => api.post(`/api/projects/${projectId}/stop-server`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-generated-apps"] }),
  });

  if (isLoading) return <AdminLayout title="Generated Apps"><LoadingState label="Loading apps..." /></AdminLayout>;

  return (
    <AdminLayout title="All Generated Apps" subtitle="Monitor and control generated applications">
      <GlassCard className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 border-b border-white/10">
              <th className="text-left p-4">App</th>
              <th className="text-left p-4">Owner</th>
              <th className="text-left p-4">Project</th>
              <th className="text-left p-4">Stack</th>
              <th className="text-left p-4">Port</th>
              <th className="text-left p-4">Status</th>
              <th className="text-left p-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((app) => (
              <tr key={app.project_id} className="border-b border-white/5">
                <td className="p-4 text-white">{app.app_name}</td>
                <td className="p-4 text-slate-400">{app.owner_user_id ?? "legacy"}</td>
                <td className="p-4 font-mono text-slate-400">{app.project_id}</td>
                <td className="p-4 text-slate-300">{typeof app.stack === "string" ? app.stack : JSON.stringify(app.stack)}</td>
                <td className="p-4 text-cyan-400">{app.server_port}</td>
                <td className="p-4">
                  <StatusBadge tone={app.running ? "success" : "warning"}>{app.running ? "Running" : "Stopped"}</StatusBadge>
                </td>
                <td className="p-4">
                  <div className="flex gap-2">
                    {app.running && (
                      <a
                        href={`http://127.0.0.1:${app.server_port}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 text-xs"
                      >
                        <ExternalLink className="w-3 h-3" /> Open
                      </a>
                    )}
                    {app.running && (
                      <button
                        onClick={() => stopMutation.mutate(app.project_id)}
                        className="text-xs text-amber-300 hover:text-amber-200"
                      >
                        Stop
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
    </AdminLayout>
  );
}
