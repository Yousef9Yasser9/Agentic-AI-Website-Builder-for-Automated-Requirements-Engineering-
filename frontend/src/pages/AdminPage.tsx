import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, FolderKanban, Layers3, RefreshCw, Server, ShieldCheck, Users } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { GlassCard } from "../components/ui/GlassCard";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { PageHeader } from "../components/ui/PageHeader";
import { fetchAdminProjects, fetchAdminStats, fetchAdminUsers, updateAdminUser } from "../services/adminService";
import { getErrorMessage } from "../services/api";
import { useToastStore } from "../stores/toastStore";
import type { AuthUser } from "../types/auth";

interface AdminProject {
  project_id: string;
  project_title: string;
  stage: string;
  saved_at?: string;
  generated_app_status?: string;
  owner_user_id?: number | null;
}

export function AdminPage() {
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);
  const [page, setPage] = useState(1);
  const [busyUser, setBusyUser] = useState<number | null>(null);
  const statsQuery = useQuery({ queryKey: ["admin-stats"], queryFn: fetchAdminStats });
  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: fetchAdminUsers });
  const projectsQuery = useQuery({ queryKey: ["admin-projects"], queryFn: fetchAdminProjects });
  const users = usersQuery.data || [];
  const projects = (projectsQuery.data || []) as AdminProject[];
  const pagedUsers = useMemo(() => users.slice((page - 1) * 10, page * 10), [page, users]);
  const pageCount = Math.max(1, Math.ceil(users.length / 10));

  const updateUser = async (user: AuthUser, payload: { is_active?: boolean; role?: "user" | "admin" }) => {
    setBusyUser(user.id);
    try {
      await updateAdminUser(user.id, payload);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-stats"] }),
      ]);
      addToast({ title: "User updated", description: `${user.full_name}'s account was updated.`, type: "success" });
    } catch (caught) {
      addToast({ title: "Update failed", description: getErrorMessage(caught), type: "error" });
    } finally {
      setBusyUser(null);
    }
  };

  const stats = [
    { label: "Total Users", value: statsQuery.data?.total_users ?? 0, icon: Users, tone: "bg-primary/10 text-blue-300" },
    { label: "Verified Users", value: statsQuery.data?.verified_users ?? 0, icon: ShieldCheck, tone: "bg-success/10 text-emerald-300" },
    { label: "Total Projects", value: statsQuery.data?.total_projects ?? 0, icon: FolderKanban, tone: "bg-secondary/10 text-violet-300" },
    { label: "Completed Builds", value: statsQuery.data?.total_generated_apps ?? 0, icon: Layers3, tone: "bg-accent/10 text-cyan-300" },
  ];

  return (
    <PageWrapper>
      <PageHeader title="Admin Console" subtitle="Monitor platform activity, manage user access, and review all project checkpoints." eyebrow="Restricted workspace" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => { const Icon = stat.icon; return <GlassCard key={stat.label} padding="md"><div className="flex items-center justify-between"><div><p className="text-sm text-text-secondary">{stat.label}</p><p className="mt-2 text-3xl font-bold text-white">{statsQuery.isLoading ? "..." : stat.value}</p></div><span className={`grid h-11 w-11 place-items-center rounded-xl ${stat.tone}`}><Icon className="h-5 w-5" /></span></div></GlassCard>; })}
      </div>

      {statsQuery.data?.system_warnings.length ? <div className="mt-5 rounded-2xl border border-warning/20 bg-warning/10 p-4 text-sm text-amber-200">{statsQuery.data.system_warnings.join(" | ")}</div> : null}

      <GlassCard padding="md" className="mt-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className={`grid h-11 w-11 place-items-center rounded-xl ${statsQuery.data?.ollama_online ? "bg-success/10 text-emerald-300" : "bg-danger/10 text-red-300"}`}><Server className="h-5 w-5" /></span>
            <div><h2 className="font-bold text-white">AI infrastructure</h2><p className="mt-1 text-sm text-text-muted">Backend API is online. Ollama model service is {statsQuery.data?.ollama_online ? "available" : "unavailable"}.</p></div>
          </div>
          <div className="flex items-center gap-3"><Badge variant={statsQuery.data?.ollama_online ? "success" : "danger"}>Ollama {statsQuery.data?.ollama_online ? "online" : "offline"}</Badge><button type="button" onClick={() => statsQuery.refetch()} className="rounded-lg border border-line p-2 text-text-secondary hover:border-line-bright hover:text-white" aria-label="Refresh infrastructure status"><RefreshCw className={`h-4 w-4 ${statsQuery.isFetching ? "animate-spin" : ""}`} /></button></div>
        </div>
      </GlassCard>

      <GlassCard className="mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b border-line p-5"><div><h2 className="text-lg font-bold text-white">Users</h2><p className="mt-1 text-sm text-text-muted">Role and account status controls</p></div><Badge variant="purple">{users.length} accounts</Badge></div>
        {usersQuery.isLoading ? <LoadingSpinner variant="skeleton" className="m-5 h-64" /> : usersQuery.error ? <div className="p-5"><EmptyState title="Users are unavailable" description={getErrorMessage(usersQuery.error)} /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-line bg-white/[0.025] text-xs uppercase tracking-[0.14em] text-text-muted"><tr><th className="px-5 py-3">User</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Created</th><th className="px-5 py-3 text-right">Actions</th></tr></thead>
              <tbody className="divide-y divide-line">
                {pagedUsers.map((user) => <tr key={user.id}><td className="px-5 py-4"><div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 text-xs font-bold text-white">{user.full_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("")}</span><div><p className="font-semibold text-white">{user.full_name}</p><p className="text-xs text-text-muted">{user.email}</p></div></div></td><td className="px-5 py-4"><Badge variant={user.role === "admin" ? "purple" : "info"}>{user.role}</Badge></td><td className="px-5 py-4"><Badge variant={user.is_active ? "success" : "danger"}>{user.is_active ? "active" : "inactive"}</Badge></td><td className="px-5 py-4 text-text-secondary">{new Date(user.created_at).toLocaleDateString(undefined, { dateStyle: "medium" })}</td><td className="px-5 py-4"><div className="flex justify-end gap-2"><button type="button" disabled={busyUser === user.id} onClick={() => updateUser(user, { is_active: !user.is_active })} className="rounded-lg border border-line px-3 py-2 text-xs font-semibold text-text-secondary hover:border-line-bright hover:text-white disabled:opacity-50">{user.is_active ? "Disable" : "Activate"}</button><button type="button" disabled={busyUser === user.id} onClick={() => updateUser(user, { role: user.role === "admin" ? "user" : "admin" })} className="rounded-lg border border-secondary/20 bg-secondary/10 px-3 py-2 text-xs font-semibold text-violet-200 disabled:opacity-50">Make {user.role === "admin" ? "User" : "Admin"}</button></div></td></tr>)}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex items-center justify-between border-t border-line p-4"><p className="text-xs text-text-muted">Page {page} of {pageCount}</p><div className="flex gap-2"><button type="button" disabled={page === 1} onClick={() => setPage((current) => current - 1)} className="rounded-lg border border-line px-3 py-2 text-xs text-text-secondary disabled:opacity-40">Previous</button><button type="button" disabled={page === pageCount} onClick={() => setPage((current) => current + 1)} className="rounded-lg border border-line px-3 py-2 text-xs text-text-secondary disabled:opacity-40">Next</button></div></div>
      </GlassCard>

      <GlassCard className="mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b border-line p-5"><div><h2 className="text-lg font-bold text-white">All Projects</h2><p className="mt-1 text-sm text-text-muted">Checkpoints across every account</p></div><Badge variant="info">{projects.length} projects</Badge></div>
        {projectsQuery.isLoading ? <LoadingSpinner variant="skeleton" className="m-5 h-52" /> : projectsQuery.error ? <div className="p-5"><EmptyState title="Projects are unavailable" description={getErrorMessage(projectsQuery.error)} /></div> : (
          <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="border-b border-line bg-white/[0.025] text-xs uppercase tracking-[0.14em] text-text-muted"><tr><th className="px-5 py-3">Name</th><th className="px-5 py-3">Owner</th><th className="px-5 py-3">Stage</th><th className="px-5 py-3">Output</th><th className="px-5 py-3">Saved</th></tr></thead><tbody className="divide-y divide-line">{projects.map((project) => <tr key={project.project_id}><td className="px-5 py-4"><p className="font-semibold text-white">{project.project_title}</p><p className="text-xs text-text-muted">{project.project_id}</p></td><td className="px-5 py-4 text-text-secondary">{project.owner_user_id ?? "Legacy"}</td><td className="px-5 py-4"><Badge>{project.stage.replaceAll("_", " ")}</Badge></td><td className="px-5 py-4"><Badge variant={project.generated_app_status === "running" ? "success" : project.generated_app_status === "built" ? "info" : "default"}>{project.generated_app_status || "none"}</Badge></td><td className="px-5 py-4 text-text-secondary">{project.saved_at ? new Date(project.saved_at).toLocaleDateString(undefined, { dateStyle: "medium" }) : "Unknown"}</td></tr>)}</tbody></table></div>
        )}
      </GlassCard>
      <p className="mt-5 flex items-center gap-2 text-xs text-text-muted"><Activity className="h-3.5 w-3.5" /> Admin data is loaded from protected backend endpoints and degrades gracefully when unavailable.</p>
    </PageWrapper>
  );
}
