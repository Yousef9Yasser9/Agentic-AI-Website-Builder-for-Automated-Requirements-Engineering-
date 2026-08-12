import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { FolderKanban, MoreHorizontal, Plus, Search, Trash2, WandSparkles } from "lucide-react";
import { CreateProjectModal } from "../components/projects/CreateProjectModal";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Badge } from "../components/ui/Badge";
import { ConfirmModal } from "../components/ui/ConfirmModal";
import { EmptyState } from "../components/ui/EmptyState";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { PageHeader } from "../components/ui/PageHeader";
import { ProgressRing } from "../components/ui/ProgressRing";
import { StageProgressStrip } from "../components/builder/StageProgressStrip";
import { deleteProject, listProjects } from "../services/projectsService";
import { getErrorMessage } from "../services/api";
import { useToastStore } from "../stores/toastStore";
import type { ProjectSummary, StageKey } from "../types/project";
import { stageOrder } from "../types/workflow";

type Filter = "all" | "active" | "building" | "completed";

function projectStatus(project: ProjectSummary): Exclude<Filter, "all"> {
  if (["PREVIEW", "BUILD_AND_RUN"].includes(project.stage)) return "completed";
  if (project.stage === "CODE_GENERATION") return "building";
  return "active";
}

export function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProjectSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const projects = projectsQuery.data || [];

  const filtered = useMemo(() => projects.filter((project) => {
    const matchesSearch = `${project.project_title} ${project.project_id}`.toLowerCase().includes(search.toLowerCase());
    return matchesSearch && (filter === "all" || projectStatus(project) === filter);
  }), [filter, projects, search]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteProject(deleteTarget.project_id);
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      addToast({ title: "Project deleted", description: `${deleteTarget.project_title} was removed.`, type: "success" });
      setDeleteTarget(null);
    } catch (caught) {
      addToast({ title: "Delete failed", description: getErrorMessage(caught), type: "error" });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <PageWrapper>
      <PageHeader
        title="My Projects"
        subtitle="Search, continue, and manage every AI application workflow in your workspace."
        actions={<GradientButton onClick={() => setCreateOpen(true)} icon={<Plus className="h-4 w-4" />}>New Project</GradientButton>}
      />

      <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-line bg-surface/60 p-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} className="input-field pl-10" placeholder="Search projects..." />
        </div>
        <select value={filter} onChange={(event) => setFilter(event.target.value as Filter)} className="input-field sm:w-44" aria-label="Filter projects">
          <option value="all">All projects</option>
          <option value="active">Active</option>
          <option value="building">Building</option>
          <option value="completed">Completed</option>
        </select>
        <Badge variant="info" className="justify-center sm:self-center">{projects.length} projects</Badge>
      </div>

      {projectsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((item) => <LoadingSpinner key={item} variant="skeleton" className="h-60" />)}</div>
      ) : projectsQuery.error ? (
        <EmptyState title="Projects could not be loaded" description={getErrorMessage(projectsQuery.error)} actionLabel="Try Again" onAction={() => projectsQuery.refetch()} />
      ) : filtered.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((project) => {
            const status = projectStatus(project);
            const stageNumber = stageOrder.indexOf(project.stage as StageKey) + 1;
            const progress = Math.max(0, Math.round((stageNumber / stageOrder.length) * 100));
            return (
              <GlassCard key={project.project_id} hover padding="md" className="group">
                <div className="flex items-start justify-between gap-3">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 text-blue-200"><FolderKanban className="h-5 w-5" /></span>
                  <div className="flex items-center gap-2">
                    <ProgressRing progress={progress} size={56} strokeWidth={6} label="done" />
                    <Badge variant={status === "completed" ? "success" : status === "building" ? "info" : "default"} className={status === "building" ? "animate-pulse" : ""}>{status}</Badge>
                    <button type="button" className="rounded-lg p-1.5 text-text-muted hover:bg-white/5 hover:text-white" aria-label="Project actions"><MoreHorizontal className="h-4 w-4" /></button>
                  </div>
                </div>
                <h2 className="mt-5 truncate text-lg font-bold text-white">{project.project_title}</h2>
                <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-text-secondary">Current stage: {project.stage.replaceAll("_", " ").toLowerCase()}.</p>
                <div className="mt-5 flex items-center justify-between text-xs text-text-muted"><span>Pipeline progress</span><span>{stageNumber}/{stageOrder.length} stages</span></div>
                <StageProgressStrip project={project} className={status === "building" ? "mt-3 animate-pulse" : "mt-3"} />
                <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
                  <span className="text-xs text-text-muted">{project.saved_at ? new Date(project.saved_at).toLocaleDateString(undefined, { dateStyle: "medium" }) : "Local checkpoint"}</span>
                  <div className="flex gap-1">
                    <button type="button" onClick={() => navigate(`/builder?project=${project.project_id}`)} className="rounded-lg p-2 text-blue-300 hover:bg-primary/10" aria-label="Open builder"><WandSparkles className="h-4 w-4" /></button>
                    <button type="button" onClick={() => navigate(`/projects/${project.project_id}`)} className="rounded-lg px-2.5 py-2 text-xs font-semibold text-text-secondary hover:bg-white/5 hover:text-white">Details</button>
                    <button type="button" onClick={() => setDeleteTarget(project)} className="rounded-lg p-2 text-text-muted hover:bg-danger/10 hover:text-red-300" aria-label="Delete project"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      ) : (
        <EmptyState icon={FolderKanban} title={projects.length ? "No matching projects" : "No projects yet"} description={projects.length ? "Try a different search or filter." : "Start building your first application from a plain-language idea."} actionLabel={projects.length ? "Clear Filters" : "Create Project"} onAction={() => projects.length ? (setSearch(""), setFilter("all")) : setCreateOpen(true)} />
      )}

      <CreateProjectModal isOpen={createOpen} onClose={() => setCreateOpen(false)} onCreated={(project) => {
        addToast({ title: "Project created", description: "Opening the workflow builder.", type: "success" });
        navigate(`/builder?project=${project.project_id}`);
      }} />
      <ConfirmModal isOpen={Boolean(deleteTarget)} onCancel={() => setDeleteTarget(null)} onConfirm={handleDelete} title="Delete project?" message={`This permanently removes "${deleteTarget?.project_title}". Generated checkpoints for this project will also be deleted.`} confirmText="Delete Project" variant="danger" loading={deleting} />
    </PageWrapper>
  );
}
