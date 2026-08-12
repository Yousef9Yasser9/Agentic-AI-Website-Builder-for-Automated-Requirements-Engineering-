import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, ChevronDown, Circle, Download, ExternalLink, FileCode2, Pencil, Play, Trash2 } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Badge } from "../components/ui/Badge";
import { ConfirmModal } from "../components/ui/ConfirmModal";
import { EmptyState } from "../components/ui/EmptyState";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { ProgressBar } from "../components/ui/ProgressBar";
import { StageProgressStrip } from "../components/builder/StageProgressStrip";
import { WorkflowPreview } from "../components/builder/WorkflowPreview";
import { artifactUrl, deleteProject, getProject } from "../services/projectsService";
import { getProjectLogs } from "../services/generationService";
import { getErrorMessage } from "../services/api";
import { useToastStore } from "../stores/toastStore";
import type { ProjectData, StageKey } from "../types/project";
import { WORKFLOW_STAGES, stageOrder } from "../types/workflow";

type Tab = "overview" | "stages" | "output" | "settings";

function stageContent(data: ProjectData, doneKey: string): unknown {
  return data[doneKey];
}

function renderValue(value: unknown) {
  if (typeof value === "string") return <div className="whitespace-pre-wrap text-sm leading-6 text-text-secondary">{value}</div>;
  return <pre className="max-h-[28rem] overflow-auto rounded-xl bg-black/30 p-4 font-mono text-xs leading-6 text-slate-300">{JSON.stringify(value, null, 2)}</pre>;
}

export function ProjectDetailsPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);
  const [tab, setTab] = useState<Tab>("overview");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const projectQuery = useQuery({ queryKey: ["project", id], queryFn: () => getProject(id), enabled: Boolean(id) });
  const logsQuery = useQuery({ queryKey: ["project-logs", id], queryFn: () => getProjectLogs(id), enabled: Boolean(id) && tab === "output", retry: false });
  const project = projectQuery.data;

  const completed = useMemo(() => {
    if (!project) return 0;
    return WORKFLOW_STAGES.filter((stage) => Boolean(project.project_data[stage.doneKey])).length;
  }, [project]);
  const progress = Math.round((completed / WORKFLOW_STAGES.length) * 100);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteProject(id);
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      addToast({ title: "Project deleted", type: "success" });
      navigate("/projects", { replace: true });
    } catch (caught) {
      addToast({ title: "Delete failed", description: getErrorMessage(caught), type: "error" });
    } finally {
      setDeleting(false);
    }
  };

  if (projectQuery.isLoading) return <LoadingSpinner variant="skeleton" className="h-[32rem]" />;
  if (!project) return <EmptyState title="Project not found" description={projectQuery.error ? getErrorMessage(projectQuery.error) : "This checkpoint does not exist or you do not have access."} actionLabel="Back to Projects" onAction={() => navigate("/projects")} />;

  const currentIndex = stageOrder.indexOf(project.stage as StageKey);
  const files = Array.isArray(project.project_data.generated_files) ? project.project_data.generated_files : [];
  const runningUrl = project.project_data.server_pid && project.server_port ? `http://127.0.0.1:${project.server_port}` : null;

  return (
    <PageWrapper>
      <Link to="/projects" className="mb-5 inline-flex items-center gap-2 text-sm text-text-secondary hover:text-white"><ArrowLeft className="h-4 w-4" /> Back to projects</Link>
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight text-white">{project.project_title}</h1>
            <button type="button" onClick={() => addToast({ title: "Profile editing is coming soon", description: "The current backend does not expose a project rename endpoint.", type: "info" })} className="rounded-lg p-2 text-text-muted hover:bg-white/5 hover:text-white" aria-label="Rename project"><Pencil className="h-4 w-4" /></button>
            <Badge variant={project.stage === "PREVIEW" ? "success" : "info"}>{project.stage.replaceAll("_", " ")}</Badge>
          </div>
          <p className="mt-2 text-sm text-text-muted">Checkpoint ID: {project.project_id}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <GradientButton onClick={() => navigate(`/builder?project=${project.project_id}`)} icon={<Play className="h-4 w-4" />}>Open Builder</GradientButton>
          <GradientButton variant="danger" onClick={() => setDeleteOpen(true)} icon={<Trash2 className="h-4 w-4" />}>Delete</GradientButton>
        </div>
      </div>

      <div className="mt-8 flex gap-1 overflow-x-auto border-b border-line">
        {(["overview", "stages", "output", "settings"] as Tab[]).map((item) => (
          <button key={item} type="button" onClick={() => setTab(item)} className={`border-b-2 px-4 py-3 text-sm font-semibold capitalize transition ${tab === item ? "border-primary text-white" : "border-transparent text-text-muted hover:text-text-secondary"}`}>{item}</button>
        ))}
      </div>

      {tab === "overview" ? (
        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_26rem]">
          <div className="grid gap-4 sm:grid-cols-2">
            <GlassCard padding="md"><p className="text-xs uppercase tracking-[0.16em] text-text-muted">Current stage</p><p className="mt-3 text-lg font-bold text-white">{project.stage.replaceAll("_", " ")}</p><p className="mt-2 text-sm text-text-secondary">{WORKFLOW_STAGES[currentIndex]?.description || "Workflow checkpoint"}</p></GlassCard>
            <GlassCard padding="md"><p className="text-xs uppercase tracking-[0.16em] text-text-muted">Completion</p><p className="mt-3 text-3xl font-bold text-white">{progress}%</p><ProgressBar value={progress} className="mt-4" /><StageProgressStrip project={project} className="mt-4" /></GlassCard>
            <GlassCard padding="md"><p className="text-xs uppercase tracking-[0.16em] text-text-muted">Generated output</p><p className="mt-3 text-lg font-bold text-white">{project.project_data.repo_path ? "Available" : "Not generated"}</p><p className="mt-2 text-sm text-text-secondary">{project.project_data.repo_path || "Complete the code generation stage to create an app."}</p></GlassCard>
            <GlassCard padding="md"><p className="text-xs uppercase tracking-[0.16em] text-text-muted">Server</p><p className="mt-3 text-lg font-bold text-white">{runningUrl ? "Running" : "Stopped"}</p><p className="mt-2 text-sm text-text-secondary">{project.server_port ? `Reserved port ${project.server_port}` : "No server assigned"}</p></GlassCard>
          </div>
          <GlassCard padding="md">
            <h2 className="text-lg font-bold text-white">Workflow progress</h2>
            <WorkflowPreview project={project} activeStage={project.stage as StageKey} variant="compact" />
          </GlassCard>
        </div>
      ) : null}

      {tab === "stages" ? (
        <div className="mt-6 space-y-3">
          {WORKFLOW_STAGES.map((stage) => {
            const content = stageContent(project.project_data, stage.doneKey);
            const open = expanded === stage.key;
            return (
              <GlassCard key={stage.key} className="overflow-hidden">
                <button type="button" onClick={() => setExpanded(open ? null : stage.key)} className="flex w-full items-center justify-between gap-4 p-5 text-left">
                  <div className="flex items-center gap-3"><span className={`grid h-9 w-9 place-items-center rounded-xl ${content ? "bg-success/10 text-success" : "bg-white/5 text-text-muted"}`}>{content ? <Check className="h-4 w-4" /> : <Circle className="h-4 w-4" />}</span><div><p className="font-semibold text-white">{stage.label}</p><p className="text-xs text-text-muted">{content ? "Output available" : "Not completed"}</p></div></div>
                  <ChevronDown className={`h-5 w-5 text-text-muted transition ${open ? "rotate-180" : ""}`} />
                </button>
                {open ? <div className="border-t border-line p-5">{content ? renderValue(content) : <p className="text-sm text-text-muted">Run this stage in the builder to create output.</p>}</div> : null}
              </GlassCard>
            );
          })}
        </div>
      ) : null}

      {tab === "output" ? (
        <div className="mt-6 grid gap-6 xl:grid-cols-2">
          <GlassCard padding="md">
            <div className="flex items-center justify-between"><h2 className="text-lg font-bold text-white">Generated application</h2>{runningUrl ? <a href={runningUrl} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-sm font-semibold text-blue-300">Open app <ExternalLink className="h-4 w-4" /></a> : null}</div>
            {project.project_data.repo_path ? <div className="mt-4 rounded-xl bg-black/30 p-4 font-mono text-xs text-text-secondary">{project.project_data.repo_path}</div> : <p className="mt-4 text-sm text-text-muted">No generated repository yet.</p>}
            {project.project_data.srs_document ? <a href={artifactUrl(project.project_id, "srs")} className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-blue-300"><Download className="h-4 w-4" /> Download SRS</a> : null}
          </GlassCard>
          <GlassCard padding="md">
            <h2 className="text-lg font-bold text-white">Generated files</h2>
            <div className="mt-4 space-y-2">
              {files.length ? files.map((file) => <div key={file.path} className="flex items-center justify-between rounded-xl border border-line bg-white/[0.025] p-3"><span className="flex min-w-0 items-center gap-2 text-sm text-text-secondary"><FileCode2 className="h-4 w-4 shrink-0 text-blue-300" /><span className="truncate">{file.name || file.path}</span></span><Badge>{file.size ? `${file.size} B` : "file"}</Badge></div>) : <p className="text-sm text-text-muted">The backend has not returned a file manifest for this project.</p>}
            </div>
          </GlassCard>
          <GlassCard padding="md" className="xl:col-span-2">
            <h2 className="text-lg font-bold text-white">Build logs</h2>
            <pre className="mt-4 max-h-80 overflow-auto rounded-xl bg-black/40 p-4 font-mono text-xs leading-6 text-emerald-300">{logsQuery.isLoading ? "Loading logs..." : logsQuery.data?.logs?.length ? logsQuery.data.logs.join("\n") : "No runtime logs recorded yet."}</pre>
          </GlassCard>
        </div>
      ) : null}

      {tab === "settings" ? (
        <div className="mt-6 grid gap-6 xl:grid-cols-2">
          <GlassCard padding="md"><h2 className="text-lg font-bold text-white">Project details</h2><label className="mt-5 block text-sm text-text-secondary">Project name<input className="input-field mt-2" defaultValue={project.project_title} /></label><label className="mt-4 block text-sm text-text-secondary">Project ID<input className="input-field mt-2" value={project.project_id} readOnly /></label><GradientButton className="mt-5" onClick={() => addToast({ title: "Project editing is coming soon", description: "The backend currently exposes checkpoints but no rename endpoint.", type: "info" })}>Save Changes</GradientButton></GlassCard>
          <GlassCard padding="md" className="border-danger/25"><h2 className="text-lg font-bold text-red-300">Danger zone</h2><p className="mt-2 text-sm leading-6 text-text-secondary">Deleting a project permanently removes its checkpoint and cannot be undone.</p><GradientButton variant="danger" className="mt-5" onClick={() => setDeleteOpen(true)} icon={<Trash2 className="h-4 w-4" />}>Delete Project</GradientButton></GlassCard>
        </div>
      ) : null}

      <ConfirmModal isOpen={deleteOpen} onCancel={() => setDeleteOpen(false)} onConfirm={handleDelete} loading={deleting} title="Delete this project?" message={`"${project.project_title}" and its checkpoint data will be permanently removed.`} confirmText="Delete Project" variant="danger" />
    </PageWrapper>
  );
}
