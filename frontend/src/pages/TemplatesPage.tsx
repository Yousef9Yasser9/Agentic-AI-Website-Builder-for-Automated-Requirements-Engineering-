import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { BarChart3, BookOpen, CalendarDays, Cloud, FileBox, LayoutDashboard, MessageSquare, Network, ShoppingBag, Sparkles, Users, Workflow } from "lucide-react";
import { CreateProjectModal } from "../components/projects/CreateProjectModal";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Badge } from "../components/ui/Badge";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { PageHeader } from "../components/ui/PageHeader";
import { useToastStore } from "../stores/toastStore";

type Category = "All" | "E-commerce" | "SaaS" | "Portfolio" | "Dashboard" | "API";
interface Template {
  name: string;
  category: Exclude<Category, "All">;
  description: string;
  stack: string[];
  complexity: "Starter" | "Intermediate" | "Advanced";
  icon: LucideIcon;
  idea: string;
}

const categoryPreview: Record<Exclude<Category, "All">, "store" | "dashboard" | "portfolio" | "api"> = {
  "E-commerce": "store",
  SaaS: "dashboard",
  Portfolio: "portfolio",
  Dashboard: "dashboard",
  API: "api",
};

const templates: Template[] = [
  { name: "E-commerce Store", category: "E-commerce", description: "Catalog, cart, checkout, orders, inventory, and admin operations.", stack: ["FastAPI", "SQLite", "Bootstrap"], complexity: "Intermediate", icon: ShoppingBag, idea: "Build an e-commerce store with customer registration, searchable products, categories, cart, checkout, order history, inventory tracking, and an admin dashboard for products and orders." },
  { name: "SaaS Dashboard", category: "SaaS", description: "Subscription workspace with teams, usage metrics, and role-based access.", stack: ["FastAPI", "JWT", "Charts"], complexity: "Advanced", icon: Cloud, idea: "Create a SaaS dashboard with organizations, member invitations, role-based access, subscription plans, usage metrics, billing history, notifications, and an admin area." },
  { name: "Portfolio Site", category: "Portfolio", description: "Project showcase, case studies, contact leads, and a simple CMS.", stack: ["FastAPI", "HTML/CSS", "SQLite"], complexity: "Starter", icon: Sparkles, idea: "Create a modern portfolio website with an editable profile, projects, case studies, skills, testimonials, contact form submissions, and an admin area to manage all content." },
  { name: "REST API Backend", category: "API", description: "Secure resource API with validation, pagination, auth, and docs.", stack: ["FastAPI", "Pydantic", "JWT"], complexity: "Starter", icon: Network, idea: "Build a documented REST API backend with JWT authentication, users and roles, CRUD resources, filtering, pagination, validation, audit timestamps, seed data, and automated tests." },
  { name: "Real-time Chat App", category: "SaaS", description: "Channels, direct messages, team presence, and moderation.", stack: ["FastAPI", "WebSockets", "SQLite"], complexity: "Advanced", icon: MessageSquare, idea: "Build a team chat application with workspaces, channels, direct messages, message search, reactions, presence, file metadata, moderation controls, and role-based administration." },
  { name: "Task Manager", category: "SaaS", description: "Projects, boards, tasks, priorities, comments, and deadlines.", stack: ["FastAPI", "SQLite", "Kanban"], complexity: "Intermediate", icon: Workflow, idea: "Create a collaborative task manager with projects, kanban boards, tasks, assignees, labels, comments, due dates, priorities, activity history, and team roles." },
  { name: "Blog Platform", category: "Portfolio", description: "Publishing workflow with categories, drafts, comments, and authors.", stack: ["FastAPI", "Markdown", "SQLite"], complexity: "Intermediate", icon: BookOpen, idea: "Create a multi-author blog platform with drafts, publishing, categories, tags, markdown content, comments, author profiles, search, and an editorial admin dashboard." },
  { name: "CRM System", category: "Dashboard", description: "Leads, companies, pipeline stages, tasks, and sales reporting.", stack: ["FastAPI", "SQLite", "Charts"], complexity: "Advanced", icon: Users, idea: "Build a CRM with contacts, companies, leads, opportunity pipeline stages, notes, follow-up tasks, ownership, sales reports, and role-based team access." },
  { name: "Analytics Dashboard", category: "Dashboard", description: "Metrics, comparisons, reports, saved filters, and exports.", stack: ["FastAPI", "Charts", "Reports"], complexity: "Intermediate", icon: BarChart3, idea: "Create an analytics dashboard with KPI cards, date filters, trend charts, comparison reports, saved views, data tables, export history, and admin-managed datasets." },
  { name: "Booking System", category: "SaaS", description: "Services, availability, reservations, reminders, and staff schedules.", stack: ["FastAPI", "Calendar", "SQLite"], complexity: "Intermediate", icon: CalendarDays, idea: "Build a booking system with services, staff availability, customer reservations, time-slot validation, cancellations, booking status, reminders, and a staff management dashboard." },
  { name: "Social Network", category: "SaaS", description: "Profiles, posts, follows, reactions, comments, and moderation.", stack: ["FastAPI", "JWT", "Feeds"], complexity: "Advanced", icon: Users, idea: "Create a social network with profiles, posts, follows, personalized feeds, likes, comments, notifications, privacy settings, reports, and moderator tools." },
  { name: "File Manager", category: "Dashboard", description: "Folder hierarchy, file metadata, sharing permissions, and activity.", stack: ["FastAPI", "Storage", "RBAC"], complexity: "Intermediate", icon: FileBox, idea: "Build a file manager with nested folders, upload metadata, search, tags, sharing permissions, recent files, favorites, storage usage, activity logs, and admin controls." },
  { name: "Operations Console", category: "Dashboard", description: "A focused command center for teams, incidents, and service health.", stack: ["FastAPI", "SQLite", "Monitoring"], complexity: "Advanced", icon: LayoutDashboard, idea: "Create an operations console with services, health status, incidents, owners, runbooks, maintenance windows, activity logs, alert acknowledgements, and role-based access." },
];

export function TemplatesPage() {
  const navigate = useNavigate();
  const addToast = useToastStore((state) => state.addToast);
  const [category, setCategory] = useState<Category>("All");
  const [selected, setSelected] = useState<Template | null>(null);
  const filtered = useMemo(() => category === "All" ? templates : templates.filter((template) => template.category === category), [category]);

  return (
    <PageWrapper>
      <PageHeader title="Project Templates" subtitle="Start from a detailed product brief, then customize every stage of the generated application." />
      <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
        {(["All", "E-commerce", "SaaS", "Portfolio", "Dashboard", "API"] as Category[]).map((item) => (
          <button key={item} type="button" onClick={() => setCategory(item)} className={`whitespace-nowrap rounded-xl border px-4 py-2 text-sm font-semibold transition ${category === item ? "border-primary/40 bg-primary/15 text-blue-200" : "border-line bg-white/[0.025] text-text-secondary hover:border-line-bright hover:text-white"}`}>{item}</button>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((template) => {
          const Icon = template.icon;
          const preview = categoryPreview[template.category];
          return (
            <GlassCard key={template.name} hover className="overflow-hidden">
              <div className="relative h-40 overflow-hidden bg-gradient-to-br from-primary/20 via-secondary/15 to-primary/10 p-5">
                <div className="grid-bg absolute inset-0 opacity-40" />
                <div className="absolute -right-10 -top-12 h-36 w-36 rounded-full bg-primary/25 blur-2xl" />
                <div className="relative flex items-start justify-between"><span className="grid h-12 w-12 place-items-center rounded-2xl border border-white/15 bg-black/20 text-white"><Icon className="h-6 w-6" /></span><Badge variant="purple">{template.category}</Badge></div>
                <div className="relative mt-5 rounded-2xl border border-white/15 bg-black/25 p-3 shadow-panel">
                  {preview === "store" ? (
                    <div className="grid grid-cols-3 gap-2">{[0, 1, 2].map((item) => <span key={item} className="h-10 rounded-xl bg-gradient-to-br from-primary/50 to-secondary/40" />)}</div>
                  ) : preview === "portfolio" ? (
                    <div className="flex items-center gap-3"><span className="h-12 w-12 rounded-full bg-gradient-to-br from-primary to-secondary" /><span className="space-y-2"><span className="block h-2 w-28 rounded-full bg-white/50" /><span className="block h-2 w-20 rounded-full bg-white/25" /></span></div>
                  ) : preview === "api" ? (
                    <div className="space-y-2 font-mono text-[10px] text-white/75"><p><span className="text-blue-300">GET</span> /api/resources</p><p><span className="text-violet-300">POST</span> /api/resources</p></div>
                  ) : (
                    <div className="grid grid-cols-[1fr_1.4fr] gap-2"><span className="h-16 rounded-xl bg-white/15" /><span className="space-y-2">{[72, 100, 56].map((width) => <span key={width} className="block h-3 rounded-full bg-white/25" style={{ width: `${width}%` }} />)}</span></div>
                  )}
                </div>
              </div>
              <div className="p-5">
                <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-bold text-white">{template.name}</h2><Badge variant={template.complexity === "Starter" ? "success" : template.complexity === "Advanced" ? "warning" : "info"}>{template.complexity}</Badge></div>
                <p className="mt-3 min-h-12 text-sm leading-6 text-text-secondary">{template.description}</p>
                <div className="mt-4 flex flex-wrap gap-2">{template.stack.map((tech) => <Badge key={tech}>{tech}</Badge>)}</div>
                <GradientButton className="mt-5" fullWidth variant="secondary" onClick={() => setSelected(template)}>Use Template</GradientButton>
              </div>
            </GlassCard>
          );
        })}
      </div>
      <CreateProjectModal isOpen={Boolean(selected)} initialIdea={selected?.idea || ""} onClose={() => setSelected(null)} onCreated={(project) => {
        addToast({ title: "Template project created", description: `${selected?.name || "Template"} is ready to configure.`, type: "success" });
        navigate(`/builder?project=${project.project_id}`);
      }} />
    </PageWrapper>
  );
}
