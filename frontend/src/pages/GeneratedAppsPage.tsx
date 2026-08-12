import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ExternalLink, FileCode2, Layers3, Play, Search, Server, Square } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { EmptyState } from "../components/ui/EmptyState";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { PageHeader } from "../components/ui/PageHeader";
import { StageProgressStrip } from "../components/builder/StageProgressStrip";
import { getProject, listProjects } from "../services/projectsService";
import { startServer, stopServer } from "../services/buildService";
import { getErrorMessage } from "../services/api";
import { useToastStore } from "../stores/toastStore";

export function GeneratedAppsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const appsQuery = useQuery({
    queryKey: ["generated-apps"],
    queryFn: async () => {
      const summaries = await listProjects();
      const candidates = summaries.filter((project) => ["CODE_GENERATION", "BUILD_AND_RUN", "PREVIEW"].includes(project.stage));
      const details = await Promise.all(candidates.map((project) => getProject(project.project_id)));
      return details.filter((project) => Boolean(project.project_data.repo_path && project.project_data.tdd_passed === true));
    },
  });
  const apps = useMemo(() => (appsQuery.data || []).filter((app) => app.project_title.toLowerCase().includes(search.toLowerCase())), [appsQuery.data, search]);

  const toggleServer = async (projectId: string, running: boolean) => {
    setBusyId(projectId);
    try {
      const result = running ? await stopServer(projectId) : await startServer(projectId);
      addToast({ title: running ? "Application stopped" : "Application started", description: !running && "url" in result ? result.url : undefined, type: "success" });
      await queryClient.invalidateQueries({ queryKey: ["generated-apps"] });
    } catch (caught) {
      addToast({ title: "Runtime action failed", description: getErrorMessage(caught), type: "error" });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <PageWrapper>
      <PageHeader title="Generated Applications" subtitle="Launch, inspect, and continue working on projects that already have generated code." actions={<GradientButton onClick={() => navigate("/builder")} icon={<Play className="h-4 w-4" />}>Generate New App</GradientButton>} />
      <div className="relative mb-6 max-w-lg">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input value={search} onChange={(event) => setSearch(event.target.value)} className="input-field pl-10" placeholder="Search generated apps..." />
      </div>
      {appsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((item) => <LoadingSpinner key={item} variant="skeleton" className="h-72" />)}</div>
      ) : appsQuery.error ? (
        <EmptyState title="Applications could not be loaded" description={getErrorMessage(appsQuery.error)} actionLabel="Try Again" onAction={() => appsQuery.refetch()} />
      ) : apps.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {apps.map((app) => {
            const running = Boolean(app.project_data.server_pid);
            const url = `http://127.0.0.1:${app.server_port}`;
            const statusLabel = running ? "Running" : app.project_data.build_done ? "Built" : "Generated";
            const statusTone = running
              ? "border-success/30 bg-success/10 text-emerald-300"
              : app.project_data.build_done
                ? "border-success/30 bg-success/10 text-emerald-300"
                : "border-warning/30 bg-warning/10 text-amber-300";
            return (
              <GlassCard key={app.project_id} hover padding="md" className="relative overflow-hidden">
                <div className={`absolute inset-x-0 top-0 h-1 ${running || app.project_data.build_done ? "bg-success" : "bg-warning animate-pulse"}`} />
                <div className="flex items-start justify-between gap-3">
                  <span className={`grid h-12 w-12 place-items-center rounded-2xl border ${statusTone} ${running ? "shadow-glow" : ""}`}><Layers3 className="h-6 w-6" /></span>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusTone}`}>{statusLabel}</span>
                </div>
                <h2 className="mt-5 text-lg font-bold text-white">{app.project_title}</h2>
                <p className="mt-1 text-xs text-text-muted">Project {app.project_id}</p>
                <div className="mt-5 space-y-3">
                  <div className="flex items-center justify-between rounded-xl bg-white/[0.03] p-3 text-sm"><span className="flex items-center gap-2 text-text-secondary"><FileCode2 className="h-4 w-4 text-blue-300" /> Repository</span><span className="text-emerald-300">Ready</span></div>
                  <div className="flex items-center justify-between rounded-xl bg-white/[0.03] p-3 text-sm"><span className="flex items-center gap-2 text-text-secondary"><Server className="h-4 w-4 text-violet-300" /> Port</span><span className="font-mono text-white">{app.server_port}</span></div>
                </div>
                <StageProgressStrip project={app} className="mt-4" />
                <p className="mt-4 line-clamp-2 break-all font-mono text-xs leading-5 text-text-muted">{app.project_data.repo_path}</p>
                <div className="mt-5 grid grid-cols-2 gap-2 border-t border-line pt-4">
                  {running ? <a href={url} target="_blank" rel="noreferrer" className="btn-primary px-3 py-2 text-sm"><ExternalLink className="h-4 w-4" /> Open App</a> : <GradientButton size="sm" loading={busyId === app.project_id} onClick={() => toggleServer(app.project_id, false)} icon={<Play className="h-4 w-4" />}>Start</GradientButton>}
                  {running ? <GradientButton size="sm" variant="danger" loading={busyId === app.project_id} onClick={() => toggleServer(app.project_id, true)} icon={<Square className="h-4 w-4" />}>Stop</GradientButton> : <GradientButton size="sm" variant="secondary" onClick={() => navigate(`/projects/${app.project_id}`)}>Details</GradientButton>}
                </div>
              </GlassCard>
            );
          })}
        </div>
      ) : (
        <EmptyState icon={Layers3} title={search ? "No matching applications" : "No generated applications yet"} description={search ? "Try another search term." : "Complete code generation for a project and it will appear here."} actionLabel={search ? "Clear Search" : "Open Builder"} onAction={() => search ? setSearch("") : navigate("/builder")} />
      )}
    </PageWrapper>
  );
}
