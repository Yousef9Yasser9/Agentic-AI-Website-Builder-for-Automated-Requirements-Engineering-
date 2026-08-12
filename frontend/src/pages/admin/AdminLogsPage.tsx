import { useQuery } from "@tanstack/react-query";
import { Terminal } from "lucide-react";
import { AdminLayout } from "../../components/layout/AdminLayout";
import { GlassCard } from "../../components/ui/GlassCard";
import { LoadingState } from "../../components/ui/LoadingState";
import { fetchAdminLogs } from "../../services/adminService";

export function AdminLogsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-logs"], queryFn: fetchAdminLogs, refetchInterval: 15000 });

  if (isLoading) return <AdminLayout title="System Logs"><LoadingState label="Loading logs..." /></AdminLayout>;

  const logs = data?.logs || [];

  return (
    <AdminLayout title="System Logs" subtitle="Recent builder, generation, and system events">
      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Terminal className="w-5 h-5 text-cyan-400" />
          <h3 className="text-lg font-semibold text-white">Recent Logs ({logs.length})</h3>
        </div>
        <div className="space-y-2 max-h-[70vh] overflow-y-auto font-mono text-xs">
          {logs.length === 0 && <p className="text-slate-500">No logs recorded yet.</p>}
          {logs.map((entry, index) => (
            <div key={`${entry.project_id}-${index}`} className="p-3 rounded-lg bg-black/30 border border-white/5">
              <span className="text-cyan-400">[{entry.project_id}]</span>{" "}
              <span className="text-slate-300">{entry.message}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </AdminLayout>
  );
}
