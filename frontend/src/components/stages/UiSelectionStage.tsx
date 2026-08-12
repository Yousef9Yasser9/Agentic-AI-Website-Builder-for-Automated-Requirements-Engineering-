import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, LayoutDashboard, Palette, PanelTop, Save, Sparkles } from "lucide-react";
import { saveUiSelection } from "../../services/workflowService";
import { getErrorMessage } from "../../services/api";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { Badge } from "../ui/Badge";
import type { StageProps } from "./stageTypes";

const themes = [
  { theme_name: "Midnight Blue", ui_key: "midnight_blue", ui_description: "Deep navy surfaces with blue and violet highlights.", swatches: ["bg-blue-500", "bg-violet-500", "bg-slate-950", "bg-slate-800"], theme_vars: { primary: "#3b82f6", accent: "#8b5cf6", bg: "#070b14", surface: "#131a24" } },
  { theme_name: "Aurora Cyan", ui_key: "aurora_cyan", ui_description: "Cyan-led glass surfaces with bright technical accents.", swatches: ["bg-cyan-500", "bg-blue-500", "bg-slate-950", "bg-cyan-950"], theme_vars: { primary: "#06b6d4", accent: "#3b82f6", bg: "#071017", surface: "#10202a" } },
  { theme_name: "Emerald Studio", ui_key: "emerald_studio", ui_description: "Calm emerald accents for operational and data-heavy tools.", swatches: ["bg-emerald-500", "bg-teal-500", "bg-slate-950", "bg-emerald-950"], theme_vars: { primary: "#10b981", accent: "#14b8a6", bg: "#07120f", surface: "#10211c" } },
  { theme_name: "Violet Product", ui_key: "violet_product", ui_description: "Expressive violet and pink details for creative products.", swatches: ["bg-violet-500", "bg-pink-500", "bg-zinc-950", "bg-violet-950"], theme_vars: { primary: "#8b5cf6", accent: "#ec4899", bg: "#0d0914", surface: "#1d1428" } },
];

const layouts = [
  { layout_name: "Top Navigation", layout_key: "top_nav", icon: PanelTop, description: "Ideal for public-facing products and broad content." },
  { layout_name: "Sidebar Navigation", layout_key: "sidebar", icon: LayoutDashboard, description: "Best for dashboards, admin tools, and dense workflows." },
];

export function UiSelectionStage({ project, onProjectChange, onStageChange }: StageProps) {
  const existing = project?.project_data.ui_selection;
  const [themeKey, setThemeKey] = useState(existing?.ui_key || themes[0].ui_key);
  const [layoutKey, setLayoutKey] = useState(existing?.layout_key || layouts[1].layout_key);
  const selectedTheme = themes.find((theme) => theme.ui_key === themeKey) || themes[0];
  const selectedLayout = layouts.find((layout) => layout.layout_key === layoutKey) || layouts[1];
  const payload = useMemo(() => ({
    theme_name: selectedTheme.theme_name,
    layout_name: selectedLayout.layout_name,
    ui_key: selectedTheme.ui_key,
    layout_key: selectedLayout.layout_key,
    ui_description: selectedTheme.ui_description,
    theme_vars: selectedTheme.theme_vars,
    layout_requirements: selectedLayout.layout_key === "sidebar" ? ["Persistent sidebar", "Responsive mobile drawer"] : ["Responsive top navigation", "Compact mobile menu"],
  }), [selectedLayout, selectedTheme]);
  const mutation = useMutation({
    mutationFn: () => saveUiSelection(project!.project_id, payload),
    onSuccess: (nextProject) => {
      onProjectChange(nextProject);
      onStageChange("CODE_GENERATION");
    },
  });

  if (!project?.project_data.data_model) return <div className="rounded-xl border border-warning/20 bg-warning/10 p-4 text-sm text-amber-200">Generate the data model before choosing the UI direction.</div>;

  return (
    <div className="space-y-6">
      <GlassCard padding="md" className="border-secondary/20 bg-secondary/5"><div className="flex items-start gap-3"><Sparkles className="mt-0.5 h-5 w-5 text-violet-300" /><div><h2 className="font-bold text-white">Choose the generated application&apos;s visual system</h2><p className="mt-1 text-sm leading-6 text-text-secondary">This selection is sent to the backend and influences layout, color tokens, and component styling.</p></div></div></GlassCard>
      <div>
        <h3 className="mb-4 flex items-center gap-2 font-bold text-white"><Palette className="h-5 w-5 text-violet-300" /> Theme</h3>
        <div className="grid gap-4 md:grid-cols-2">
          {themes.map((theme) => <button key={theme.ui_key} type="button" onClick={() => setThemeKey(theme.ui_key)} className={`glass-card p-5 text-left transition hover:border-line-bright ${themeKey === theme.ui_key ? "border-secondary/50 bg-secondary/10" : ""}`}><div className="flex items-start justify-between"><div><h4 className="font-bold text-white">{theme.theme_name}</h4><p className="mt-2 text-sm leading-6 text-text-secondary">{theme.ui_description}</p></div>{themeKey === theme.ui_key ? <span className="grid h-7 w-7 place-items-center rounded-full bg-secondary text-white"><Check className="h-4 w-4" /></span> : null}</div><div className="mt-5 grid grid-cols-4 gap-2">{theme.swatches.map((swatch) => <span key={swatch} className={`h-10 rounded-lg border border-white/10 ${swatch}`} />)}</div></button>)}
        </div>
      </div>
      <div>
        <h3 className="mb-4 font-bold text-white">Layout</h3>
        <div className="grid gap-4 md:grid-cols-2">
          {layouts.map((layout) => { const Icon = layout.icon; return <button key={layout.layout_key} type="button" onClick={() => setLayoutKey(layout.layout_key)} className={`glass-card p-5 text-left transition hover:border-line-bright ${layoutKey === layout.layout_key ? "border-primary/50 bg-primary/10" : ""}`}><div className="flex items-center justify-between"><span className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-blue-300"><Icon className="h-5 w-5" /></span>{layoutKey === layout.layout_key ? <Badge variant="info">Selected</Badge> : null}</div><h4 className="mt-4 font-bold text-white">{layout.layout_name}</h4><p className="mt-2 text-sm text-text-secondary">{layout.description}</p></button>; })}
        </div>
      </div>
      {mutation.error ? <div className="rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-red-300">{getErrorMessage(mutation.error)}</div> : null}
      <GlassCard padding="md"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-bold text-white">{selectedTheme.theme_name} + {selectedLayout.layout_name}</p><p className="mt-1 text-sm text-text-secondary">Ready to save and continue to code generation.</p></div><GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()} icon={<Save className="h-4 w-4" />}>Save & Continue</GradientButton></div></GlassCard>
    </div>
  );
}
