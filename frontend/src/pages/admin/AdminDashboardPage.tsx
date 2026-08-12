import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, CheckCircle2, Code, Folder, Server, ShieldCheck, Users } from "lucide-react";
import { AdminLayout } from "../../components/layout/AdminLayout";
import { Badge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { GlassCard } from "../../components/ui/GlassCard";
import { LoadingState } from "../../components/ui/LoadingState";
import { ProgressBar } from "../../components/ui/ProgressBar";
import { ProgressRing } from "../../components/ui/ProgressRing";
import { fetchAdminStats } from "../../services/adminService";

export function AdminDashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-stats"], queryFn: fetchAdminStats });

  if (isLoading) return <AdminLayout title="Admin Dashboard"><LoadingState label="Loading dashboard..." /></AdminLayout>;

  const totalUsers = data?.total_users ?? 0;
  const verifiedUsers = data?.verified_users ?? 0;
  const totalProjects = data?.total_projects ?? 0;
  const generatedApps = data?.total_generated_apps ?? 0;
  const runningApps = data?.active_running_apps ?? 0;
  const verifiedRate = totalUsers ? Math.round((verifiedUsers / totalUsers) * 100) : 0;
  const generatedRate = totalProjects ? Math.round((generatedApps / totalProjects) * 100) : 0;
  const runningRate = generatedApps ? Math.round((runningApps / generatedApps) * 100) : 0;
  const stats = [
    { label: "Total Users", value: totalUsers, icon: Users, color: "from-cyan-500 to-blue-500", meta: `${verifiedUsers} verified` },
    { label: "Disabled Users", value: data?.disabled_users ?? 0, icon: AlertTriangle, color: "from-amber-500 to-orange-500", meta: "Account controls" },
    { label: "Total Projects", value: totalProjects, icon: Folder, color: "from-purple-500 to-pink-500", meta: `${generatedApps} generated` },
    { label: "Running Apps", value: runningApps, icon: Server, color: "from-cyan-500 to-purple-500", meta: `${runningRate}% of generated` },
  ];

  return (
    <AdminLayout title="Admin Dashboard" subtitle="Restricted operations console for users, projects, models, and runtime health.">
      <section className="premium-section mb-8 p-6">
        <div className="relative z-10 grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div>
            <Badge variant={data?.ollama_online ? "success" : "danger"}>
              <ShieldCheck className="h-3.5 w-3.5" /> {data?.ollama_online ? "Ollama online" : "Ollama offline"}
            </Badge>
            <h2 className="mt-4 text-2xl font-black tracking-tight text-white">Platform control room</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
              Monitor real backend counts, account health, generated repositories, and model availability without mixing admin data into the normal workspace.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-line bg-white/[0.035] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">Verified users</p>
                <ProgressBar value={verifiedRate} showLabel className="mt-3" />
              </div>
              <div className="rounded-2xl border border-line bg-white/[0.035] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">Generated apps</p>
                <ProgressBar value={generatedRate} showLabel className="mt-3" />
              </div>
              <div className="rounded-2xl border border-line bg-white/[0.035] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">Running apps</p>
                <ProgressBar value={runningRate} showLabel className="mt-3" />
              </div>
            </div>
          </div>
          <div className="grid place-items-center rounded-3xl border border-primary/15 bg-primary/10 p-5">
            <ProgressRing progress={verifiedRate} size={140} strokeWidth={10} color="#22d3ee" label="verified" />
          </div>
        </div>
      </section>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <GlassCard key={stat.label} hover className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-secondary">{stat.label}</p>
                  <p className="mt-1 text-3xl font-bold text-white">{stat.value}</p>
                  <p className="mt-2 text-xs text-text-muted">{stat.meta}</p>
                </div>
                <div className={`rounded-xl bg-gradient-to-r p-3 shadow-glow ${stat.color}`}>
                  <Icon className="h-5 w-5 text-white" />
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <GlassCard className="p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">AI Infrastructure</h3>
            <Badge variant={data?.ollama_online ? "success" : "danger"}>{data?.ollama_online ? "Online" : "Offline"}</Badge>
          </div>
          {data?.system_warnings?.length ? (
            <div className="mt-4 space-y-2">
              {data.system_warnings.map((w) => (
                <p key={w} className="flex items-center gap-2 rounded-xl border border-warning/20 bg-warning/10 p-3 text-sm text-amber-300">
                  <AlertTriangle className="h-4 w-4" /> {w}
                </p>
              ))}
            </div>
          ) : (
            <p className="mt-4 flex items-center gap-2 rounded-xl border border-success/20 bg-success/10 p-3 text-sm text-emerald-300">
              <CheckCircle2 className="h-4 w-4" /> No system warnings reported.
            </p>
          )}
        </GlassCard>

        <GlassCard className="p-6">
          <h3 className="mb-4 text-lg font-semibold text-white">Recent Users</h3>
          <div className="space-y-3">
            {(data?.recent_users || []).length ? (data?.recent_users || []).map((user) => (
              <div key={user.id ?? user.email} className="flex items-center justify-between gap-3 rounded-xl border border-line bg-white/[0.025] p-3 text-sm">
                <span className="min-w-0">
                  <span className="block truncate font-semibold text-white">{user.full_name}</span>
                  <span className="block truncate text-xs text-text-muted">{user.email}</span>
                </span>
                <span className="rounded-full border border-primary/20 bg-primary/10 px-2 py-1 text-xs font-semibold text-blue-300">{user.role}</span>
              </div>
            )) : <EmptyState title="No recent users" description="User activity will appear here after accounts are created." />}
          </div>
        </GlassCard>

        <GlassCard className="p-6 lg:col-span-2">
          <h3 className="mb-4 text-lg font-semibold text-white">Recent Projects</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-text-muted">
                  <th className="py-2 text-left">Title</th>
                  <th className="py-2 text-left">ID</th>
                  <th className="py-2 text-left">Stage</th>
                  <th className="py-2 text-left">Generated</th>
                </tr>
              </thead>
              <tbody>
                {(data?.recent_projects || []).length ? (data?.recent_projects || []).map((p) => (
                  <tr key={p.project_id} className="border-b border-white/5">
                    <td className="py-3 font-semibold text-white">{p.project_title}</td>
                    <td className="py-3 font-mono text-xs text-text-muted">{p.project_id}</td>
                    <td className="py-3 text-cyan-300">{p.stage}</td>
                    <td className="py-3 text-text-secondary">{p.generated_app_status || "Pending"}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={4} className="py-8">
                      <EmptyState title="No projects yet" description="Projects created by users will appear in this operations table." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>
    </AdminLayout>
  );
}
