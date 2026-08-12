import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Code2, FileCode2, Rocket, TimerReset } from "lucide-react";
import { generateCode, getProjectLogs } from "../../services/generationService";
import { getErrorMessage } from "../../services/api";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { Badge } from "../ui/Badge";
import { LogPanel } from "../ui/LogPanel";
import { ProgressBar } from "../ui/ProgressBar";
import type { StageProps } from "./stageTypes";

export function CodeGenerationStage({ project, onProjectChange, onStageChange }: StageProps) {
  const [options, setOptions] = useState({
    build_from_scratch: true,
    run_tdd: true,
    run_refactor: false,
    debug_logging: false,
  });
  const [logs, setLogs] = useState<string[]>([]);
  const mutation = useMutation({
    mutationFn: async () => {
      if (!project?.project_id) throw new Error("Create a project before generating code.");
      setLogs(["Preparing blueprint...", "Resolving files and dependencies...", "Starting code generation..."]);
      const next = await generateCode(project.project_id, options);
      setLogs((current) => [...current, "Repository generated successfully.", "Checkpoint saved."]);
      return next;
    },
    onSuccess: (next) => onProjectChange(next),
    onError: (caught) => setLogs((current) => [...current, `Error: ${getErrorMessage(caught)}`]),
  });

  useEffect(() => {
    if (!mutation.isPending || !project?.project_id) return;
    let active = true;
    const loadLogs = async () => {
      try {
        const response = await getProjectLogs(project.project_id);
        if (active && response.logs.length) setLogs(response.logs);
      } catch {
        // Keep the local optimistic logs if polling briefly fails.
      }
    };
    loadLogs();
    const timer = window.setInterval(loadLogs, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [mutation.isPending, project?.project_id]);

  if (!project?.project_data.ui_selection) {
    return <div className="rounded-xl border border-warning/20 bg-warning/10 p-4 text-sm text-amber-200">Select a UI direction before generating code.</div>;
  }

  const generated = Boolean(project.project_data.repo_path);
  const toggles = [
    { key: "run_tdd", label: "TDD loop", description: "Generate and execute automated tests." },
    { key: "run_refactor", label: "Refactor pass", description: "Run an additional quality pass after generation." },
    { key: "debug_logging", label: "Debug logging", description: "Include verbose diagnostics in the generated app." },
  ] as const;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-5">
        <GlassCard padding="lg" className="relative overflow-hidden border-primary/20">
          <div className="absolute right-0 top-0 h-56 w-56 rounded-full bg-primary/10 blur-3xl" />
          <div className="relative">
            <Badge variant={generated ? "success" : "info"}>{generated ? "Repository ready" : "Generation configured"}</Badge>
            <h2 className="mt-4 text-2xl font-bold text-white">{generated ? "Your application was generated" : "Generate the complete application"}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">The generator uses your requirements, architecture, data model, SRS, and UI selection to create a working FastAPI application.</p>
            {generated ? (
              <div className="mt-6 rounded-xl border border-success/20 bg-success/10 p-4">
                <p className="flex items-center gap-2 font-semibold text-emerald-300"><Check className="h-4 w-4" /> Generation complete</p>
                <p className="mt-2 break-all font-mono text-xs text-text-secondary">{project.project_data.repo_path}</p>
                <GradientButton className="mt-4" onClick={() => onStageChange("BUILD_AND_RUN")} icon={<Rocket className="h-4 w-4" />}>Continue to Build</GradientButton>
              </div>
            ) : (
              <GradientButton className="mt-6" size="lg" loading={mutation.isPending} onClick={() => mutation.mutate()} icon={<Code2 className="h-5 w-5" />}>{mutation.isPending ? "Generating application..." : "Generate Application"}</GradientButton>
            )}
            {mutation.isPending ? (
              <div className="mt-5 flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/10 p-4 text-sm text-blue-100">
                <TimerReset className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
                <p>
                  Code generation is running through local Ollama and can take a few minutes. The log panel polls the backend checkpoint logs while the request is active.
                </p>
              </div>
            ) : null}
            {mutation.error ? <div className="mt-5 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-red-300">{getErrorMessage(mutation.error)}</div> : null}
          </div>
        </GlassCard>

        <GlassCard padding="md">
          <h3 className="font-bold text-white">Generation options</h3>
          <div className="mt-4 space-y-2">
            {toggles.map((toggle) => (
              <label key={toggle.key} className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-line bg-white/[0.025] p-4">
                <span><span className="block text-sm font-semibold text-white">{toggle.label}</span><span className="mt-1 block text-xs text-text-muted">{toggle.description}</span></span>
                <input type="checkbox" checked={options[toggle.key]} onChange={(event) => setOptions((current) => ({ ...current, [toggle.key]: event.target.checked }))} className="h-5 w-5 accent-blue-500" />
              </label>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="space-y-5">
        <GlassCard padding="md" className="border-primary/15">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-white">Generation pulse</h3>
              <p className="mt-1 text-xs text-text-muted">{mutation.isPending ? "Backend log polling is active." : "Logs will appear when generation starts."}</p>
            </div>
            <span className={`h-3 w-3 rounded-full ${mutation.isPending ? "animate-pulse bg-emerald-400 shadow-halo" : "bg-white/15"}`} />
          </div>
          {mutation.isPending ? <ProgressBar value={68} animated className="mt-4" /> : null}
        </GlassCard>
        <LogPanel logs={logs.map((line) => `> ${line}`)} title="Generation log" />
        <div className="mt-5 space-y-2">
          {["FastAPI backend", "Database models", "Authentication", "Responsive UI", "Seed data", "Automated tests"].map((item) => <div key={item} className="flex items-center gap-2 text-sm text-text-secondary"><FileCode2 className="h-4 w-4 text-blue-300" /> {item}</div>)}
        </div>
      </div>
    </div>
  );
}
