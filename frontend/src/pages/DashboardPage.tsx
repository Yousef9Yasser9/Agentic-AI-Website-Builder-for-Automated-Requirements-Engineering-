import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, CheckCircle2, Clock3, FolderKanban, Layers3, Plus, Server, Sparkles, WandSparkles, Zap } from "lucide-react";
import { CreateProjectModal } from "../components/projects/CreateProjectModal";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { PageWrapper } from "../components/layout/PageWrapper";
import { ProgressBar } from "../components/ui/ProgressBar";
import { ProgressRing } from "../components/ui/ProgressRing";
import { StageProgressStrip } from "../components/builder/StageProgressStrip";
import { WorkflowPreview } from "../components/builder/WorkflowPreview";
import { useAuth } from "../contexts/AuthContext";
import { useOllamaStatus } from "../hooks/useOllamaStatus";
import { listProjects } from "../services/projectsService";
import { useToastStore } from "../stores/toastStore";
import type { ProjectSummary, StageKey } from "../types/project";
import { WORKFLOW_STAGES, stageOrder } from "../types/workflow";

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function progressFor(project: ProjectSummary) {
  const index = stageOrder.indexOf(project.stage as StageKey);
  return Math.max(9, Math.round(((index + 1) / stageOrder.length) * 100));
}

function completedFor(project: ProjectSummary) {
  if (project.project_data) {
    return WORKFLOW_STAGES.filter((stage) => Boolean(project.project_data?.[stage.doneKey])).length;
  }
  return Math.max(0, stageOrder.indexOf(project.stage as StageKey));
}

function creationActivity(projects: ProjectSummary[]) {
  const today = new Date();
  return Array.from({ length: 7 }, (_, offset) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (6 - offset));
    const key = date.toDateString();
    return {
      label: date.toLocaleDateString(undefined, { weekday: "short" }),
      count: projects.filter((project) => project.saved_at && new Date(project.saved_at).toDateString() === key).length,
    };
  });
}

function Sparkline({ data }: { data: { label: string; count: number }[] }) {
  const max = Math.max(1, ...data.map((item) => item.count));
  const points = data.map((item, index) => {
    const x = (index / Math.max(1, data.length - 1)) * 100;
    const y = 34 - (item.count / max) * 26;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg viewBox="0 0 100 40" className="mt-4 h-10 w-full overflow-visible" role="img" aria-label="Project creation over the last seven days">
      <defs>
        <linearGradient id="dashboard-sparkline" x1="0" x2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      <polyline points={points} fill="none" stroke="url(#dashboard-sparkline)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      {data.map((item, index) => {
        const x = (index / Math.max(1, data.length - 1)) * 100;
        const y = 34 - (item.count / max) * 26;
        return <circle key={item.label} cx={x} cy={y} r="2.4" fill="#3b82f6" className="drop-shadow" />;
      })}
    </svg>
  );
}

const quickStarts = [
  {
    title: "Clinic booking",
    tag: "healthcare",
    idea: "Build a clinic appointment booking system with patient booking flow, doctor schedule dashboard, admin management, appointment notes, payments, and double-booking prevention.",
  },
  {
    title: "School portal",
    tag: "education",
    idea: "Build a multi-role school management system with student dashboards, teacher course management, assignments, grades, announcements, enrollments, and admin controls.",
  },
  {
    title: "Restaurant ops",
    tag: "hospitality",
    idea: "Build a restaurant reservation and pickup ordering system with public menu, guest reservations, staff order operations, table scheduling, and admin dashboards.",
  },
];

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const addToast = useToastStore((state) => state.addToast);
  const reduceMotion = useReducedMotion();
  const [modalOpen, setModalOpen] = useState(false);
  const [initialIdea, setInitialIdea] = useState("");
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const ollamaQuery = useOllamaStatus();
  const projects = projectsQuery.data || [];
  const completedBuilds = projects.filter((project) => ["BUILD_AND_RUN", "PREVIEW"].includes(project.stage)).length;
  const generatedApps = projects.filter((project) => ["CODE_GENERATION", "BUILD_AND_RUN", "PREVIEW"].includes(project.stage)).length;
  const activeSessions = projects.filter((project) => project.stage !== "PREVIEW").length;
  const completedStages = projects.reduce((total, project) => total + completedFor(project), 0);
  const totalStages = projects.length * WORKFLOW_STAGES.length;
  const activity = creationActivity(projects);
  const recentActivity = projects
    .filter((project) => project.saved_at)
    .sort((a, b) => new Date(b.saved_at || 0).getTime() - new Date(a.saved_at || 0).getTime())
    .slice(0, 5);
  const stageDistribution = WORKFLOW_STAGES.map((stage) => ({
    stage,
    count: projects.filter((project) => project.stage === stage.key).length,
  })).filter((item) => item.count > 0);

  const stats = [
    { title: "Active Projects", value: activeSessions, icon: FolderKanban, tone: "bg-primary/10 text-blue-300", change: `${projects.length} total projects`, sparkline: true },
    { title: "Stages Completed", value: totalStages ? `${completedStages}/${totalStages}` : "0/0", icon: CheckCircle2, tone: "bg-success/10 text-emerald-300", change: "Checkpoint-backed progress" },
    { title: "Generated Apps", value: generatedApps, icon: Layers3, tone: "bg-secondary/10 text-violet-300", change: `${completedBuilds} build-ready` },
    { title: "AI Service", value: ollamaQuery.data?.online ? "Online" : "Offline", icon: Server, tone: ollamaQuery.data?.online ? "bg-success/10 text-emerald-300" : "bg-danger/10 text-red-300", change: ollamaQuery.data?.models?.[0] || "Ollama status" },
  ];
  const openQuickStart = (idea: string) => {
    setInitialIdea(idea);
    setModalOpen(true);
  };

  return (
    <PageWrapper>
      <section className="relative mb-8 overflow-hidden rounded-3xl border border-line bg-gradient-to-br from-primary/15 via-surface to-secondary/10 p-6 sm:p-8">
        <div className="grid-bg absolute inset-0 opacity-40" />
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Badge variant="info"><Sparkles className="h-3.5 w-3.5" /> AI workspace online</Badge>
            <h1 className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl">{greeting()}, {user?.full_name.split(" ")[0]}</h1>
            <p className="mt-2 text-text-secondary">Here&apos;s what&apos;s happening across your application workflows.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <GradientButton onClick={() => setModalOpen(true)} icon={<Plus className="h-4 w-4" />}>New Project</GradientButton>
            <GradientButton variant="secondary" onClick={() => navigate("/builder")} icon={<WandSparkles className="h-4 w-4" />}>Open Builder</GradientButton>
          </div>
        </div>
      </section>

      <motion.section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        initial={reduceMotion ? false : "hidden"}
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.04 } } }}
      >
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.title}
              variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
            <GlassCard hover padding="md" className="h-full">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-text-secondary">{stat.title}</p>
                  <p className="mt-2 text-3xl font-bold text-white">{projectsQuery.isLoading ? "..." : stat.value}</p>
                </div>
                <span className={`grid h-11 w-11 place-items-center rounded-xl ${stat.tone}`}><Icon className="h-5 w-5" /></span>
              </div>
              {stat.sparkline ? <Sparkline data={activity} /> : <p className="mt-4 text-xs font-medium text-text-muted">{stat.change}</p>}
            </GlassCard>
            </motion.div>
          );
        })}
      </motion.section>

      <section className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <GlassCard padding="md">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Workflow pulse</h2>
              <p className="mt-1 text-sm text-text-secondary">Stage distribution across the current workspace.</p>
            </div>
            <Badge variant="purple">{stageDistribution.length || 0} active lanes</Badge>
          </div>
          <div className="mt-5 flex h-3 overflow-hidden rounded-full bg-white/[0.06]">
            {stageDistribution.length ? stageDistribution.map((item, index) => (
              <span
                key={item.stage.key}
                title={`${item.stage.label}: ${item.count}`}
                className={index % 2 === 0 ? "bg-primary" : "bg-secondary"}
                style={{ width: `${Math.max(8, (item.count / Math.max(1, projects.length)) * 100)}%` }}
              />
            )) : <span className="w-full bg-white/[0.08]" />}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {stageDistribution.length ? stageDistribution.map((item) => (
              <span key={item.stage.key} className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-blue-300">{item.stage.shortLabel}: {item.count}</span>
            )) : <span className="text-sm text-text-muted">Create a project to light up the workflow map.</span>}
          </div>
        </GlassCard>
        <GlassCard padding="md">
          <h2 className="text-lg font-bold text-white">Workflow map</h2>
          <p className="mt-1 text-sm text-text-secondary">The full pipeline at a glance.</p>
          <WorkflowPreview variant="compact" />
        </GlassCard>
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_26rem]">
        <GlassCard padding="md">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Recent activity</h2>
              <p className="mt-1 text-sm text-text-secondary">Derived from saved project checkpoints.</p>
            </div>
            <Clock3 className="h-5 w-5 text-blue-300" />
          </div>
          <div className="space-y-3">
            {recentActivity.length ? recentActivity.map((project, index) => (
              <motion.button
                key={project.project_id}
                type="button"
                onClick={() => navigate(`/builder?project=${project.project_id}`)}
                className="flex w-full items-center gap-3 rounded-2xl border border-line bg-white/[0.025] p-3 text-left transition hover:border-primary/35 hover:bg-primary/10"
                initial={reduceMotion ? false : { opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.04, duration: 0.18 }}
              >
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/10 font-mono text-xs font-black text-blue-300">{index + 1}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-white">{project.project_title}</span>
                  <span className="block font-mono text-xs text-text-muted">{new Date(project.saved_at || "").toLocaleString()}</span>
                </span>
                <Badge>{project.stage.replaceAll("_", " ")}</Badge>
              </motion.button>
            )) : <p className="rounded-2xl border border-line bg-white/[0.025] p-4 text-sm text-text-muted">No saved checkpoint activity yet.</p>}
          </div>
        </GlassCard>

        <GlassCard padding="md">
          <div className="mb-5">
            <h2 className="text-lg font-bold text-white">Quick-start templates</h2>
            <p className="mt-1 text-sm text-text-secondary">Detailed prompts for testing the full pipeline.</p>
          </div>
          <div className="space-y-3">
            {quickStarts.map((item, index) => (
              <motion.button
                key={item.title}
                type="button"
                onClick={() => openQuickStart(item.idea)}
                className="group w-full rounded-2xl border border-line bg-gradient-to-br from-white/[0.045] to-white/[0.015] p-4 text-left transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-glow"
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04, duration: 0.18 }}
              >
                <Badge variant="purple">{item.tag}</Badge>
                <p className="mt-3 font-bold text-white group-hover:text-blue-200">{item.title}</p>
                <p className="mt-2 line-clamp-2 text-sm leading-5 text-text-secondary">{item.idea}</p>
              </motion.button>
            ))}
          </div>
        </GlassCard>
      </section>

      <section className="mt-8">
        <div className="mb-4 flex items-center justify-between">
          <div><h2 className="text-xl font-bold text-white">Recent Projects</h2><p className="mt-1 text-sm text-text-secondary">Continue from your latest checkpoint.</p></div>
          <button type="button" onClick={() => navigate("/projects")} className="flex items-center gap-1.5 text-sm font-semibold text-blue-300 hover:text-blue-200">View all <ArrowRight className="h-4 w-4" /></button>
        </div>
        {projectsQuery.isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((item) => <LoadingSpinner key={item} variant="skeleton" className="h-48" />)}</div>
        ) : projects.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.slice(0, 6).map((project) => {
              const progress = progressFor(project);
              return (
                <GlassCard key={project.project_id} hover padding="md" className="group">
                  <div className="flex items-start justify-between gap-3">
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-blue-300"><FolderKanban className="h-5 w-5" /></span>
                    <ProgressRing progress={progress} size={66} strokeWidth={7} label="done" />
                  </div>
                  <Badge className="mt-4" variant={project.stage === "PREVIEW" ? "success" : project.stage === "CODE_GENERATION" ? "info" : "default"}>{project.stage.replaceAll("_", " ")}</Badge>
                  <h3 className="mt-5 truncate text-lg font-bold text-white group-hover:text-blue-200">{project.project_title}</h3>
                  <p className="mt-2 text-sm text-text-secondary">Checkpoint {project.project_id} is {progress}% through the workflow.</p>
                  <ProgressBar value={progress} className="mt-5" />
                  <StageProgressStrip project={project} className="mt-4" />
                  <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
                    <span className="text-xs text-text-muted">{project.saved_at ? new Date(project.saved_at).toLocaleDateString(undefined, { dateStyle: "medium" }) : "Local checkpoint"}</span>
                    <button type="button" onClick={() => navigate(`/builder?project=${project.project_id}`)} className="text-sm font-semibold text-blue-300 hover:text-blue-200">Open</button>
                  </div>
                </GlassCard>
              );
            })}
          </div>
        ) : (
          <EmptyState title="Create your first project" description="Describe an application idea and let the workflow turn it into a structured build." actionLabel="Create Project" onAction={() => setModalOpen(true)} />
        )}
      </section>

      {projects.length < 3 ? (
        <section className="mt-8 rounded-2xl border border-primary/20 bg-gradient-to-r from-primary/10 to-secondary/10 p-6 sm:flex sm:items-center sm:justify-between">
          <div><h2 className="text-lg font-bold text-white">Start a new project in seconds</h2><p className="mt-1 text-sm text-text-secondary">Describe the product, review each AI stage, then generate and run it.</p></div>
          <GradientButton className="mt-4 sm:mt-0" onClick={() => setModalOpen(true)} icon={<Plus className="h-4 w-4" />}>Create Project</GradientButton>
        </section>
      ) : null}

      <CreateProjectModal
        isOpen={modalOpen}
        initialIdea={initialIdea}
        onClose={() => setModalOpen(false)}
        onCreated={(project) => {
          addToast({ title: "Project created", description: "Your first checkpoint is ready.", type: "success" });
          navigate(`/builder?project=${project.project_id}`);
        }}
      />
    </PageWrapper>
  );
}
