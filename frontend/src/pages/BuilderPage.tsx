import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, CheckCircle2, Clock3, ExternalLink, LockKeyhole, Play, Save, Square, WandSparkles } from "lucide-react";
import { PlainTextStage } from "../components/stages/PlainTextStage";
import { CleanedSpecStage } from "../components/stages/CleanedSpecStage";
import { RequirementsStage } from "../components/stages/RequirementsStage";
import { UserStoriesStage } from "../components/stages/UserStoriesStage";
import { ArchitectureStage } from "../components/stages/ArchitectureStage";
import { DataModelStage } from "../components/stages/DataModelStage";
import { SrsDocumentationStage } from "../components/stages/SrsDocumentationStage";
import { UiSelectionStage } from "../components/stages/UiSelectionStage";
import { CodeGenerationStage } from "../components/stages/CodeGenerationStage";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Badge } from "../components/ui/Badge";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { LogPanel } from "../components/ui/LogPanel";
import { ProgressBar } from "../components/ui/ProgressBar";
import { BuildTimeline } from "../components/builder/BuildTimeline";
import { StageProgressStrip } from "../components/builder/StageProgressStrip";
import { useGenerationLogs } from "../hooks/useGenerationLogs";
import { buildProject, getServerStatus, startServer, stopServer } from "../services/buildService";
import { getProject, updateProjectStage } from "../services/projectsService";
import { getErrorMessage } from "../services/api";
import { useToastStore } from "../stores/toastStore";
import type { ProjectState, StageKey } from "../types/project";
import type { ServerStatus } from "../types/generation";
import { WORKFLOW_STAGES } from "../types/workflow";

function AnimatedStageTimeline({
  project,
  currentStage,
  completedCount,
  onStageChange,
}: {
  project?: ProjectState;
  currentStage: StageKey;
  completedCount: number;
  onStageChange: (stage: StageKey) => void;
}) {
  const currentIndex = WORKFLOW_STAGES.findIndex((stage) => stage.key === currentStage);
  const progressPct = Math.round((completedCount / WORKFLOW_STAGES.length) * 100);
  const railPct = Math.max(0, Math.min(100, (currentIndex / Math.max(1, WORKFLOW_STAGES.length - 1)) * 100));

  return (
    <div className="mb-6 overflow-hidden rounded-3xl border border-line bg-slate-950/35 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-col gap-4 border-b border-line/70 px-5 py-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-primary to-secondary text-white shadow-lg shadow-primary/25">
            <WandSparkles className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-300">Circular workflow</p>
            <h2 className="mt-1 text-lg font-bold text-white">Eleven animated phases</h2>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="h-2 w-40 overflow-hidden rounded-full bg-white/10">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-primary to-emerald-400"
              initial={false}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.55, ease: "easeOut" }}
            />
          </div>
          <span className="text-sm font-semibold text-text-secondary">{completedCount} / {WORKFLOW_STAGES.length}</span>
        </div>
      </div>

      <div className="scrollbar-hide overflow-x-auto">
        <div className="relative min-w-[1180px] px-7 py-7">
          <div className="absolute left-14 right-14 top-[4.15rem] h-1 rounded-full bg-white/10" />
          <motion.div
            className="absolute left-14 top-[4.15rem] h-1 rounded-full bg-gradient-to-r from-cyan-400 via-primary to-emerald-400"
            initial={false}
            animate={{ width: `calc((100% - 7rem) * ${railPct / 100})` }}
            transition={{ duration: 0.55, ease: "easeOut" }}
          />
          <div className="relative z-10 grid grid-cols-11 gap-0">
          {WORKFLOW_STAGES.map((stage, index) => {
            const Icon = stage.icon;
            const done = Boolean(project?.project_data[stage.doneKey]);
            const active = stage.key === currentStage;
            const locked = Boolean(project) ? index > Math.max(currentIndex + 1, completedCount) : index > 0;

            return (
              <div key={stage.key} className="flex flex-col items-center text-center">
                <motion.button
                  type="button"
                  disabled={locked}
                  onClick={() => onStageChange(stage.key)}
                  className={[
                    "relative grid h-20 w-20 place-items-center rounded-full border-2 transition-all disabled:cursor-not-allowed",
                    active
                      ? "border-cyan-300 bg-gradient-to-br from-cyan-500 to-blue-600 text-white shadow-2xl shadow-cyan-500/35"
                      : done
                        ? "border-emerald-300/60 bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-xl shadow-emerald-500/25"
                        : "border-slate-700/60 bg-slate-800/70 text-slate-500 opacity-50",
                  ].join(" ")}
                  initial={false}
                  animate={{ y: active ? -7 : 0, scale: active ? 1.08 : 1 }}
                  transition={{ type: "spring", stiffness: 360, damping: 20 }}
                >
                  {active ? (
                    <>
                      <motion.span
                        className="absolute -inset-3 rounded-full border border-cyan-300/35"
                        animate={{ opacity: [0.15, 0.8, 0.15], scale: [0.92, 1.1, 0.92] }}
                        transition={{ duration: 1.7, repeat: Infinity, ease: "easeInOut" }}
                      />
                      <motion.span
                        className="absolute -inset-6 rounded-full bg-cyan-400/10 blur-xl"
                        animate={{ opacity: [0.3, 0.85, 0.3] }}
                        transition={{ duration: 1.7, repeat: Infinity, ease: "easeInOut" }}
                      />
                    </>
                  ) : null}
                  <span className="relative z-10">
                    {done ? <CheckCircle2 className="h-8 w-8" /> : locked ? <LockKeyhole className="h-6 w-6" /> : <Icon className="h-8 w-8" />}
                  </span>
                </motion.button>
                <div className="mt-4 min-h-[3.5rem] px-1">
                  <p className={active ? "text-sm font-bold text-cyan-200" : done ? "text-sm font-bold text-emerald-200" : "text-sm font-bold text-slate-500"}>
                    {stage.shortLabel}
                  </p>
                  <p className="mt-1 text-[11px] leading-4 text-slate-500">{stage.label}</p>
                </div>
              </div>
            );
          })}
          </div>
        </div>
      </div>
    </div>
  );
}

function CircularWorkflowRing({
  project,
  currentStage,
  completedCount,
  onStageChange,
}: {
  project?: ProjectState;
  currentStage: StageKey;
  completedCount: number;
  onStageChange: (stage: StageKey) => void;
}) {
  const currentIndex = WORKFLOW_STAGES.findIndex((stage) => stage.key === currentStage);
  const current = WORKFLOW_STAGES[currentIndex] || WORKFLOW_STAGES[0];
  const progressPct = Math.round((completedCount / WORKFLOW_STAGES.length) * 100);
  const size = 430;
  const center = size / 2;
  const radius = 166;
  const circumference = 2 * Math.PI * radius;
  const strokeOffset = circumference - (progressPct / 100) * circumference;

  return (
    <GlassCard className="mb-6 overflow-hidden p-5 sm:p-6">
      <div className="flex flex-col gap-5 border-b border-line pb-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-blue-300">Animated pipeline</p>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-white">Eleven intelligent stages</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">
            The stage ring is driven by checkpoint state, so completed nodes, active focus, and progress always reflect the real workflow.
          </p>
        </div>
        <div className="rounded-2xl border border-primary/25 bg-primary/10 px-4 py-3 text-right">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-blue-200">Stage {currentIndex + 1} / {WORKFLOW_STAGES.length}</p>
          <p className="mt-1 text-2xl font-black text-white">{progressPct}%</p>
        </div>
      </div>

      <div className="grid gap-6 pt-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="relative mx-auto aspect-square w-full max-w-[31rem]">
          <svg viewBox={`0 0 ${size} ${size}`} className="h-full w-full" role="img" aria-label="Circular workflow progress">
            <defs>
              <linearGradient id="workflow-ring-gradient" x1="0%" x2="100%" y1="0%" y2="100%">
                <stop offset="0%" stopColor="#3b82f6" />
                <stop offset="52%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
              <filter id="workflow-ring-glow">
                <feGaussianBlur stdDeviation="5" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <circle cx={center} cy={center} r={radius} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="18" />
            <motion.circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke="url(#workflow-ring-gradient)"
              strokeWidth="18"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={false}
              animate={{ strokeDashoffset: strokeOffset }}
              transition={{ duration: 0.7, ease: "easeOut" }}
              style={{ rotate: -90, transformOrigin: "50% 50%" }}
              filter="url(#workflow-ring-glow)"
            />
            <motion.circle
              cx={center}
              cy={center - radius}
              r="7"
              fill="#ffffff"
              stroke="#06b6d4"
              strokeWidth="4"
              style={{ transformOrigin: `${center}px ${center}px` }}
              animate={{ rotate: 360 }}
              transition={{ duration: 7.5, ease: "linear", repeat: Infinity }}
            />
          </svg>

          {WORKFLOW_STAGES.map((stage, index) => {
            const Icon = stage.icon;
            const angle = -90 + (index / WORKFLOW_STAGES.length) * 360;
            const radians = (angle * Math.PI) / 180;
            const x = center + Math.cos(radians) * radius;
            const y = center + Math.sin(radians) * radius;
            const done = Boolean(project?.project_data[stage.doneKey]);
            const active = stage.key === currentStage;
            const locked = Boolean(project) ? index > Math.max(currentIndex + 1, completedCount) : index > 0;
            return (
              <motion.button
                key={stage.key}
                type="button"
                disabled={locked}
                onClick={() => onStageChange(stage.key)}
                className={[
                  "absolute grid h-14 w-14 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-2xl border transition disabled:cursor-not-allowed sm:h-16 sm:w-16",
                  active
                    ? "border-cyan-200 bg-gradient-to-br from-primary to-secondary text-white shadow-glow"
                    : done
                      ? "border-success/50 bg-success/15 text-emerald-200"
                      : "border-line bg-surface-2/90 text-text-muted opacity-60",
                ].join(" ")}
                style={{ left: `${(x / size) * 100}%`, top: `${(y / size) * 100}%` }}
                initial={false}
                animate={{ scale: active ? 1.12 : done ? 1.02 : 0.94, y: active ? -3 : 0 }}
                transition={{ type: "spring", stiffness: 330, damping: 20 }}
              >
                {active ? (
                  <motion.span
                    className="absolute -inset-3 rounded-3xl border border-cyan-300/40"
                    animate={{ opacity: [0.25, 0.85, 0.25], scale: [0.92, 1.12, 0.92] }}
                    transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                  />
                ) : null}
                <span className="relative z-10">{done ? <CheckCircle2 className="h-6 w-6" /> : locked ? <LockKeyhole className="h-5 w-5" /> : <Icon className="h-6 w-6" />}</span>
              </motion.button>
            );
          })}

          <div className="absolute left-1/2 top-1/2 w-[56%] -translate-x-1/2 -translate-y-1/2 rounded-[2rem] border border-line bg-surface/85 p-5 text-center shadow-2xl shadow-black/30 backdrop-blur-xl">
            <motion.div
              className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-white"
              animate={{ scale: [1, 1.06, 1] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
            >
              {(() => { const Icon = current.icon || WandSparkles; return <Icon className="h-6 w-6" />; })()}
            </motion.div>
            <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-blue-300">Stage {currentIndex + 1} / {WORKFLOW_STAGES.length} - {progressPct}%</p>
            <h3 className="mt-2 text-xl font-black text-white">{current.label}</h3>
            <p className="mt-2 text-sm leading-5 text-text-secondary">{current.description}</p>
          </div>
        </div>

        <div className="space-y-3">
          {WORKFLOW_STAGES.map((stage, index) => {
            const done = Boolean(project?.project_data[stage.doneKey]);
            const active = stage.key === currentStage;
            const locked = Boolean(project) ? index > Math.max(currentIndex + 1, completedCount) : index > 0;
            return (
              <button
                key={stage.key}
                type="button"
                disabled={locked}
                onClick={() => onStageChange(stage.key)}
                className={`flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition disabled:cursor-not-allowed ${active ? "border-primary/45 bg-primary/12 text-white shadow-glow" : done ? "border-success/20 bg-success/10 text-emerald-100" : "border-line bg-white/[0.025] text-text-secondary opacity-75"}`}
              >
                <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl font-mono text-xs font-black ${done ? "bg-success/15 text-success" : active ? "bg-primary/15 text-blue-200" : "bg-white/5 text-text-muted"}`}>
                  {done ? <Check className="h-4 w-4" /> : locked ? <LockKeyhole className="h-4 w-4" /> : String(index + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-bold">{stage.shortLabel}</span>
                  <span className="block truncate text-xs text-text-muted">{stage.label}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </GlassCard>
  );
}

function BuildStage({ project, onProjectChange, onStageChange }: {
  project?: ProjectState;
  onProjectChange: (project: ProjectState) => void;
  onStageChange: (stage: StageKey) => void;
}) {
  const addToast = useToastStore((state) => state.addToast);
  const mutation = useMutation({
    mutationFn: () => buildProject(project!.project_id),
    onSuccess: (next) => {
      onProjectChange(next);
      addToast({ title: "Build completed", description: "The generated application is ready to start.", type: "success" });
    },
  });
  if (!project?.project_data.repo_path || project.project_data.tdd_passed !== true) {
    return <div className="rounded-xl border border-warning/20 bg-warning/10 p-4 text-sm text-amber-200">Complete code generation with passing runtime tests before starting the build.</div>;
  }
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <GlassCard padding="lg">
        <Badge variant="purple">Stage 10</Badge>
        <h2 className="mt-4 text-2xl font-bold text-white">Build and validate</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">Create an isolated environment, install dependencies, seed the database, and verify the generated repository.</p>
        {mutation.error ? <div className="mt-5 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-red-300">{getErrorMessage(mutation.error)}</div> : null}
        <GradientButton className="mt-6" size="lg" loading={mutation.isPending} onClick={() => mutation.mutate()} icon={<Play className="h-5 w-5" />}>{mutation.isPending ? "Building application..." : project.project_data.build_done ? "Rebuild Application" : "Build Application"}</GradientButton>
        {project.project_data.build_done ? <GradientButton className="mt-3 sm:ml-3 sm:mt-0" variant="secondary" onClick={() => onStageChange("PREVIEW")}>Continue to Preview</GradientButton> : null}
      </GlassCard>
      <GlassCard padding="md"><h3 className="mb-5 font-bold text-white">Build pipeline</h3><BuildTimeline active={mutation.isPending} done={Boolean(project.project_data.build_done)} files={project.project_data.generated_files} /></GlassCard>
    </div>
  );
}

function PreviewStage({ project }: { project?: ProjectState }) {
  const addToast = useToastStore((state) => state.addToast);
  const statusQuery = useQuery({ queryKey: ["server-status", project?.project_id], queryFn: () => getServerStatus(project!.project_id), enabled: Boolean(project?.project_id), refetchInterval: 4000 });
  const startMutation = useMutation({
    mutationFn: () => startServer(project!.project_id),
    onSuccess: (status) => {
      statusQuery.refetch();
      addToast({ title: "Application started", description: status.url, type: "success" });
    },
  });
  const stopMutation = useMutation({
    mutationFn: () => stopServer(project!.project_id),
    onSuccess: () => {
      statusQuery.refetch();
      addToast({ title: "Application stopped", type: "info" });
    },
  });
  const status: ServerStatus | undefined = statusQuery.data;
  if (!project?.project_data.build_done) return <div className="rounded-xl border border-warning/20 bg-warning/10 p-4 text-sm text-amber-200">Build the generated project before opening the live preview.</div>;
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <GlassCard padding="lg" className="relative overflow-hidden">
        <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-success/10 blur-3xl" />
        <div className="relative">
          <Badge variant={status?.running ? "success" : "default"}>{status?.running ? "Server running" : "Server stopped"}</Badge>
          <h2 className="mt-4 text-2xl font-bold text-white">Your application is ready</h2>
          <p className="mt-2 text-sm leading-6 text-text-secondary">Launch the generated FastAPI application, inspect its API documentation, and keep iterating from the saved checkpoint.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            {status?.running ? (
              <>
                <a href={status.url} target="_blank" rel="noreferrer" className="btn-primary"><ExternalLink className="h-4 w-4" /> Open Application</a>
                <a href={status.docs_url} target="_blank" rel="noreferrer" className="btn-secondary">API Docs</a>
                <GradientButton variant="danger" loading={stopMutation.isPending} onClick={() => stopMutation.mutate()} icon={<Square className="h-4 w-4" />}>Stop Server</GradientButton>
              </>
            ) : (
              <GradientButton size="lg" loading={startMutation.isPending} onClick={() => startMutation.mutate()} icon={<Play className="h-5 w-5" />}>{startMutation.isPending ? "Starting..." : "Start Application"}</GradientButton>
            )}
          </div>
          {(startMutation.error || stopMutation.error) ? <div className="mt-5 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-red-300">{getErrorMessage(startMutation.error || stopMutation.error)}</div> : null}
        </div>
      </GlassCard>
      <GlassCard padding="md">
        <h3 className="font-bold text-white">Runtime details</h3>
        <div className="mt-5 space-y-3">
          <div className="rounded-xl bg-white/[0.035] p-3"><p className="text-xs text-text-muted">Status</p><p className="mt-1 text-sm font-semibold text-white">{status?.running ? "Online" : "Offline"}</p></div>
          <div className="rounded-xl bg-white/[0.035] p-3"><p className="text-xs text-text-muted">Port</p><p className="mt-1 text-sm font-semibold text-white">{status?.port || project.server_port || "Pending"}</p></div>
          <div className="rounded-xl bg-white/[0.035] p-3"><p className="text-xs text-text-muted">Repository</p><p className="mt-1 break-all font-mono text-xs text-text-secondary">{project.project_data.repo_path}</p></div>
        </div>
      </GlassCard>
    </div>
  );
}

export function BuilderPage() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project") || searchParams.get("project_id") || "";
  const addToast = useToastStore((state) => state.addToast);
  const projectQuery = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId), enabled: Boolean(projectId) });
  const [project, setProject] = useState<ProjectState>();
  const [currentStage, setCurrentStage] = useState<StageKey>("PLAIN_TEXT");
  const logsQuery = useGenerationLogs(project?.project_id, Boolean(project?.project_id));

  useEffect(() => {
    if (projectQuery.data) {
      setProject(projectQuery.data);
      setCurrentStage(projectQuery.data.stage as StageKey);
    }
  }, [projectQuery.data]);

  const currentIndex = WORKFLOW_STAGES.findIndex((stage) => stage.key === currentStage);
  const completedCount = useMemo(() => project ? WORKFLOW_STAGES.filter((stage) => Boolean(project.project_data[stage.doneKey])).length : 0, [project]);
  const progress = Math.round((completedCount / WORKFLOW_STAGES.length) * 100);

  const handleStageChange = async (stage: StageKey) => {
    const targetIndex = WORKFLOW_STAGES.findIndex((item) => item.key === stage);
    const accessible = !project || targetIndex <= Math.max(currentIndex + 1, completedCount);
    if (!accessible) return;
    setCurrentStage(stage);
    if (project?.project_id) {
      try {
        const next = await updateProjectStage(project.project_id, stage);
        setProject(next);
      } catch (caught) {
        addToast({ title: "Could not change stage", description: getErrorMessage(caught), type: "error" });
      }
    }
  };

  const stageProps = { project, onProjectChange: setProject, onStageChange: handleStageChange };
  const content = (() => {
    switch (currentStage) {
      case "PLAIN_TEXT": return <PlainTextStage {...stageProps} />;
      case "CLEANED_SPEC": return <CleanedSpecStage {...stageProps} />;
      case "REQUIREMENTS": return <RequirementsStage {...stageProps} />;
      case "USER_STORIES": return <UserStoriesStage {...stageProps} />;
      case "ARCHITECTURE": return <ArchitectureStage {...stageProps} />;
      case "DATA_MODEL": return <DataModelStage {...stageProps} />;
      case "SRS_DOCUMENTATION": return <SrsDocumentationStage {...stageProps} />;
      case "UI_SELECTION": return <UiSelectionStage {...stageProps} />;
      case "CODE_GENERATION": return <CodeGenerationStage {...stageProps} />;
      case "BUILD_AND_RUN": return <BuildStage {...stageProps} />;
      case "PREVIEW": return <PreviewStage project={project} />;
    }
  })();

  if (projectId && projectQuery.isLoading) return <LoadingSpinner variant="skeleton" className="h-[38rem]" />;

  return (
    <PageWrapper>
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div><Badge variant="purple"><WandSparkles className="h-3.5 w-3.5" /> Intelligent workflow</Badge><h1 className="mt-3 text-3xl font-bold text-white">{project?.project_title || "Create a new application"}</h1><p className="mt-2 text-sm text-text-secondary">{project ? `Checkpoint ${project.project_id}` : "Start by describing the product you want to build."}</p></div>
        <div className="flex items-center gap-3"><GradientButton variant="secondary" onClick={() => addToast({ title: "Progress saved", description: "Every workflow stage is checkpointed automatically.", type: "success" })} icon={<Save className="h-4 w-4" />}>Save Progress</GradientButton></div>
      </div>

      <CircularWorkflowRing
        project={project}
        currentStage={currentStage}
        completedCount={completedCount}
        onStageChange={handleStageChange}
      />

      <div className="grid gap-5 xl:grid-cols-[250px_minmax(0,1fr)_280px]">
        <GlassCard className="h-fit overflow-hidden xl:sticky xl:top-24">
          <div className="border-b border-line p-4"><h2 className="font-bold text-white">Workflow stages</h2><p className="mt-1 text-xs text-text-muted">{completedCount} of {WORKFLOW_STAGES.length} complete</p></div>
          <div className="scrollbar-hide flex gap-2 overflow-x-auto p-3 xl:block xl:max-h-[calc(100vh-12rem)] xl:space-y-1 xl:overflow-y-auto">
            {WORKFLOW_STAGES.map((stage, index) => {
              const done = Boolean(project?.project_data[stage.doneKey]);
              const active = stage.key === currentStage;
              const locked = Boolean(project) ? index > Math.max(currentIndex + 1, completedCount) : index > 0;
              return (
                <button key={stage.key} type="button" disabled={locked} onClick={() => handleStageChange(stage.key)} className={`flex min-w-48 items-center gap-3 rounded-xl p-3 text-left transition xl:min-w-0 xl:w-full ${active ? "bg-primary/12 text-white" : done ? "text-text-secondary hover:bg-white/[0.035]" : "text-text-muted hover:bg-white/[0.025]"} disabled:cursor-not-allowed disabled:opacity-40`}>
                  <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full border text-xs font-bold ${done ? "border-success/30 bg-success/10 text-success" : active ? "border-primary/40 bg-primary/15 text-blue-300" : "border-line"}`}>{done ? <Check className="h-4 w-4" /> : locked ? <LockKeyhole className="h-3.5 w-3.5" /> : index + 1}</span>
                  <span className="min-w-0"><span className="block truncate text-sm font-semibold">{stage.shortLabel}</span><span className="block truncate text-[11px] text-text-muted">{stage.label}</span></span>
                </button>
              );
            })}
          </div>
        </GlassCard>

        <div className="min-w-0">
          <GlassCard className="mb-5 p-5">
            <div className="flex items-start gap-4">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 text-blue-200">{(() => { const Icon = WORKFLOW_STAGES[currentIndex]?.icon || WandSparkles; return <Icon className="h-5 w-5" />; })()}</span>
              <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-300">Stage {currentIndex + 1}</p><h2 className="mt-1 text-xl font-bold text-white">{WORKFLOW_STAGES[currentIndex]?.label}</h2><p className="mt-1 text-sm text-text-secondary">{WORKFLOW_STAGES[currentIndex]?.description}</p></div>
            </div>
          </GlassCard>
          {content}
        </div>

        <GlassCard padding="md" className="h-fit xl:sticky xl:top-24">
          <h2 className="font-bold text-white">Project overview</h2>
          <ProgressBar value={progress} showLabel className="mt-5" />
          <StageProgressStrip project={project} activeStage={currentStage} className="mt-4" />
          <div className="mt-6 space-y-3">
            <div className="rounded-xl bg-white/[0.035] p-3"><p className="text-xs text-text-muted">Current stage</p><p className="mt-1 text-sm font-semibold text-white">{WORKFLOW_STAGES[currentIndex]?.label}</p></div>
            <div className="rounded-xl bg-white/[0.035] p-3"><p className="text-xs text-text-muted">Stages done</p><p className="mt-1 text-sm font-semibold text-white">{completedCount} / {WORKFLOW_STAGES.length}</p></div>
            <div className="rounded-xl bg-white/[0.035] p-3"><p className="flex items-center gap-1.5 text-xs text-text-muted"><Clock3 className="h-3.5 w-3.5" /> Checkpoint</p><p className="mt-1 text-sm font-semibold text-white">{project ? "Auto-saved" : "Not created"}</p></div>
          </div>
          {project?.stage_done ? <div className="mt-5 flex items-center gap-2 rounded-xl border border-success/20 bg-success/10 p-3 text-sm text-emerald-300"><Check className="h-4 w-4" /> Current stage complete</div> : null}
          {project ? (
            <div className="mt-5 rounded-xl border border-line bg-white/[0.025] p-3">
              <p className="text-xs text-text-muted">Last checkpoint</p>
              <p className="mt-1 font-mono text-xs text-text-secondary">{project.saved_at ? new Date(project.saved_at).toLocaleString() : "Local session"}</p>
            </div>
          ) : null}
          <div className="mt-5">
            <LogPanel logs={logsQuery.data?.logs || []} title="Streaming live log" />
          </div>
        </GlassCard>
      </div>
    </PageWrapper>
  );
}
