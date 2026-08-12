import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Bell,
  BookOpen,
  ChevronDown,
  FileText,
  FolderKanban,
  Grid2X2,
  LayoutDashboard,
  Layers3,
  LogOut,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  User,
  Users,
  WandSparkles,
  X,
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useToastStore } from "../../stores/toastStore";
import { Brand } from "../ui/Brand";

const workspaceSections = [
  {
    label: "Main",
    links: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/projects", label: "Projects", icon: FolderKanban },
      { to: "/builder", label: "Builder", icon: WandSparkles },
      { to: "/generated-apps", label: "Generated Apps", icon: Layers3 },
    ],
  },
  {
    label: "Resources",
    links: [
      { to: "/templates", label: "Templates", icon: Grid2X2 },
      { to: "/docs", label: "Docs", icon: BookOpen },
    ],
  },
  {
    label: "Account",
    links: [
      { to: "/profile", label: "Profile", icon: User },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

const adminSections = [
  {
    label: "Admin",
    links: [
      { to: "/admin", label: "Console", icon: ShieldCheck },
      { to: "/admin/users", label: "Users", icon: Users },
      { to: "/admin/projects", label: "All Projects", icon: FolderKanban },
      { to: "/admin/generated-apps", label: "Generated Apps", icon: Layers3 },
    ],
  },
  {
    label: "Operations",
    links: [
      { to: "/admin/models", label: "Models", icon: SlidersHorizontal },
      { to: "/admin/system", label: "System Health", icon: Activity },
      { to: "/admin/logs", label: "Logs", icon: FileText },
    ],
  },
];

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/projects": "Projects",
  "/builder": "AI Builder",
  "/generated-apps": "Generated Apps",
  "/templates": "Templates",
  "/docs": "Documentation",
  "/profile": "Profile",
  "/settings": "Settings",
  "/admin": "Admin Console",
  "/admin/users": "User Management",
  "/admin/projects": "All Projects",
  "/admin/generated-apps": "Generated Apps",
  "/admin/models": "Model Management",
  "/admin/system": "System Health",
  "/admin/logs": "System Logs",
};

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const addToast = useToastStore((state) => state.addToast);
  const isAdmin = user?.role === "admin";
  const sections = isAdmin ? adminSections : workspaceSections;
  const title = location.pathname.startsWith("/projects/") || location.pathname.startsWith("/admin/projects/")
    ? "Project Details"
    : pageTitles[location.pathname] ?? (isAdmin ? "Admin Console" : "AI Builder");
  const initials = user?.full_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase() || "AI";
  const workspaceLabel = isAdmin ? "Restricted / Admin" : "Workspace";
  const profileLinks = isAdmin
    ? [
        { to: "/admin/models", label: "Model Settings", icon: SlidersHorizontal },
        { to: "/admin/system", label: "System Health", icon: Activity },
      ]
    : [
        { to: "/profile", label: "Profile", icon: User },
        { to: "/settings", label: "Settings", icon: Settings },
      ];

  const handleLogout = async () => {
    await logout();
    addToast({ title: "Signed out", description: "Your session has ended.", type: "info" });
    navigate("/login");
  };

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-20 items-center justify-between border-b border-line px-5">
        <Brand showTagline={isAdmin} />
        <button type="button" onClick={() => setMobileOpen(false)} className="rounded-lg p-2 text-text-muted hover:bg-white/5 hover:text-white lg:hidden" aria-label="Close navigation">
          <X className="h-5 w-5" />
        </button>
      </div>
      <nav className="scrollbar-hide flex-1 overflow-y-auto px-3 py-5">
        {sections.map((section) => (
          <div key={section.label} className="mb-6">
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-text-muted">{section.label}</p>
            <div className="space-y-1">
              {section.links.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) => `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${isActive ? "bg-primary/10 text-blue-200 before:absolute before:-left-3 before:h-6 before:w-0.5 before:rounded-full before:bg-gradient-to-b before:from-primary before:to-secondary" : "text-text-secondary hover:bg-white/[0.04] hover:text-white"}`}
                  >
                    <Icon className="h-[18px] w-[18px]" />
                    {item.label}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
        {isAdmin ? (
          <div className="rounded-2xl border border-secondary/20 bg-secondary/10 p-4">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-secondary/20 text-violet-200">
                <BarChart3 className="h-4 w-4" />
              </span>
              <div>
                <p className="text-sm font-semibold text-white">Admin mode</p>
                <p className="mt-0.5 text-xs text-text-muted">Normal workspace pages are hidden.</p>
              </div>
            </div>
          </div>
        ) : null}
      </nav>
      <div className="border-t border-line p-3">
        <div className="flex items-center gap-3 rounded-xl bg-white/[0.035] p-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-primary to-secondary text-sm font-bold text-white">{initials}</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-white">{user?.full_name}</p>
            <p className="truncate text-xs text-text-muted">{user?.email}</p>
          </div>
          <button type="button" onClick={handleLogout} className="rounded-lg p-2 text-text-muted hover:bg-danger/10 hover:text-red-300" aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="page-surface min-h-screen bg-ink text-text-primary">
      {mobileOpen ? <button type="button" className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" /> : null}
      <aside className={`fixed inset-y-0 left-0 z-50 w-[264px] border-r border-line bg-surface/95 shadow-panel backdrop-blur-2xl transition-transform duration-200 lg:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        {sidebar}
      </aside>
      <div className="lg:pl-[264px]">
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-line bg-ink/80 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setMobileOpen(true)} className="rounded-xl border border-line p-2.5 text-text-secondary hover:border-line-bright hover:text-white lg:hidden" aria-label="Open navigation">
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <p className="text-lg font-bold tracking-tight text-white">{title}</p>
              <p className="hidden text-xs text-text-muted sm:block">{workspaceLabel} / {title}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin ? (
              <span className="hidden rounded-full border border-secondary/25 bg-secondary/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] text-violet-200 xl:inline-flex">
                Restricted console
              </span>
            ) : null}
            <button type="button" className="hidden rounded-xl p-2.5 text-text-secondary hover:bg-white/5 hover:text-white sm:block" aria-label="Search">
              <Search className="h-5 w-5" />
            </button>
            <button type="button" className="relative rounded-xl p-2.5 text-text-secondary hover:bg-white/5 hover:text-white" aria-label="Notifications">
              <Bell className="h-5 w-5" />
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full border-2 border-ink bg-primary" />
            </button>
            <div className="relative">
              <button type="button" onClick={() => setProfileOpen((open) => !open)} className="flex items-center gap-2 rounded-xl border border-line bg-white/[0.035] p-1.5 pr-2 text-sm hover:border-line-bright" aria-expanded={profileOpen}>
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-primary to-secondary text-xs font-bold">{initials}</span>
                <ChevronDown className="hidden h-4 w-4 text-text-muted sm:block" />
              </button>
              {profileOpen ? (
                <div className="absolute right-0 mt-2 w-52 animate-scale-in rounded-xl border border-line bg-surface-2 p-2 shadow-panel">
                  {profileLinks.map((item) => {
                    const Icon = item.icon;
                    return (
                      <Link key={item.to} to={item.to} onClick={() => setProfileOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-secondary hover:bg-white/5 hover:text-white">
                        <Icon className="h-4 w-4" /> {item.label}
                      </Link>
                    );
                  })}
                  <button type="button" onClick={handleLogout} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-300 hover:bg-danger/10"><LogOut className="h-4 w-4" /> Logout</button>
                </div>
              ) : null}
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
