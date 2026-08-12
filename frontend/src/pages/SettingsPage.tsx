import { Bell, Database, Monitor, Moon, ShieldCheck, Sun } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { PageHeader } from "../components/ui/PageHeader";
import { resolveTheme, type ThemePreference, useThemeStore } from "../stores/themeStore";
import { useToastStore } from "../stores/toastStore";

export function SettingsPage() {
  const addToast = useToastStore((state) => state.addToast);
  const theme = useThemeStore((state) => state.theme);
  const setTheme = useThemeStore((state) => state.setTheme);
  const save = () => addToast({ title: "Preferences saved", description: "Workspace preferences were stored for this browser.", type: "success" });
  const themes: { id: ThemePreference; label: string; description: string; icon: typeof Sun }[] = [
    { id: "light", label: "Light", description: "Bright, clean workspace", icon: Sun },
    { id: "dark", label: "Dark", description: "Focused low-light UI", icon: Moon },
    { id: "system", label: "System", description: `Currently ${resolveTheme("system")}`, icon: Monitor },
  ];
  return (
    <PageWrapper>
      <PageHeader title="Settings" subtitle="Configure your workspace appearance, notifications, and project preferences." actions={<GradientButton onClick={save}>Save Preferences</GradientButton>} />
      <div className="grid gap-5 xl:grid-cols-2">
        <GlassCard padding="lg" className="xl:col-span-2">
          <h2 className="flex items-center gap-2 text-lg font-bold text-white"><Monitor className="h-5 w-5 text-blue-300" /> Appearance</h2>
          <p className="mt-2 text-sm text-text-secondary">Choose a theme for this device. System follows your operating system automatically.</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {themes.map((option) => {
              const Icon = option.icon;
              const selected = theme === option.id;
              return <button key={option.id} type="button" onClick={() => setTheme(option.id)} aria-pressed={selected} className={`rounded-xl border p-4 text-left transition ${selected ? "border-primary/50 bg-primary/10 text-blue-200 shadow-glow" : "border-line bg-white/[0.025] text-text-secondary hover:border-line-bright"}`}><Icon className="h-5 w-5" /><span className="mt-3 block text-sm font-semibold">{option.label}</span><span className="mt-1 block text-xs font-normal text-text-muted">{option.description}</span></button>;
            })}
          </div>
        </GlassCard>
        <GlassCard padding="lg"><h2 className="flex items-center gap-2 text-lg font-bold text-white"><Bell className="h-5 w-5 text-violet-300" /> Notifications</h2><div className="mt-5 space-y-3">{["Stage completed", "Build finished", "Runtime stopped", "Security notices"].map((label) => <label key={label} className="flex items-center justify-between rounded-xl border border-line bg-white/[0.025] p-4 text-sm text-text-secondary">{label}<input type="checkbox" defaultChecked className="h-5 w-5 accent-blue-500" /></label>)}</div></GlassCard>
        <GlassCard padding="lg"><h2 className="flex items-center gap-2 text-lg font-bold text-white"><Database className="h-5 w-5 text-cyan-300" /> Project data</h2><p className="mt-2 text-sm leading-6 text-text-secondary">Project checkpoints and generated repositories are stored by the local backend. Deleting a project removes its checkpoint permanently.</p><div className="mt-5 rounded-xl border border-success/20 bg-success/10 p-4 text-sm text-emerald-200"><ShieldCheck className="mr-2 inline h-4 w-4" /> Your projects are scoped to your authenticated account.</div></GlassCard>
      </div>
    </PageWrapper>
  );
}
