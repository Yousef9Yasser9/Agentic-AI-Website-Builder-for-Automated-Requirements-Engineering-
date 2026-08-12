import { useMutation } from "@tanstack/react-query";
import { Blocks } from "lucide-react";
import { generateArchitecture } from "../../services/workflowService";
import { getErrorMessage } from "../../services/api";
import { methodTone } from "../../types/workflow";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { JsonViewer } from "../ui/JsonViewer";
import { StatusBadge } from "../ui/StatusBadge";
import { ErrorState } from "../ui/ErrorState";
import type { StageProps } from "./stageTypes";

export function ArchitectureStage({ project, onProjectChange }: StageProps) {
  const arch = project?.project_data?.architecture;
  const mutation = useMutation({
    mutationFn: () => generateArchitecture(project!.project_id),
    onSuccess: onProjectChange,
  });
  if (!project?.project_data?.user_stories) return <ErrorState message="Generate user stories first." />;
  return (
    <div className="space-y-5">
      <GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()}>
        <Blocks className="h-4 w-4" />
        Generate Architecture
      </GradientButton>
      {mutation.isError ? <ErrorState message={getErrorMessage(mutation.error)} /> : null}
      {arch ? (
        <>
          <div className="grid gap-5 lg:grid-cols-3">
            <GlassCard className="p-5">
              <h3 className="mb-4 text-sm font-semibold text-white">Tech Stack</h3>
              <div className="space-y-2">
                {Object.entries(arch.stack || {}).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-3 rounded-md bg-white/[0.035] px-3 py-2 text-sm">
                    <span className="text-slate-500">{key}</span>
                    <span className="truncate font-semibold text-slate-100">{String(value)}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
            <GlassCard className="p-5 lg:col-span-2">
              <h3 className="mb-4 text-sm font-semibold text-white">Pages</h3>
              <div className="grid gap-3 md:grid-cols-2">
                {(arch.pages || []).map((page) => (
                  <div key={page.path || page.name} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                    <p className="font-semibold text-white">{page.name}</p>
                    <p className="mt-1 text-xs text-electric">{page.path}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(page.role_access || []).map((role: string) => <StatusBadge key={role}>{role}</StatusBadge>)}
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
          <GlassCard className="p-5">
            <h3 className="mb-4 text-sm font-semibold text-white">API Endpoints</h3>
            <div className="grid gap-3 lg:grid-cols-2">
              {(arch.endpoints || []).map((ep) => (
                <div key={`${ep.method}-${ep.path}`} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-md border px-2 py-1 text-xs font-bold ${methodTone[ep.method] || methodTone.GET}`}>{ep.method}</span>
                    <code className="text-sm text-slate-100">{ep.path}</code>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{ep.desc}</p>
                </div>
              ))}
            </div>
          </GlassCard>
          <JsonViewer value={arch} title="Architecture JSON" />
        </>
      ) : null}
    </div>
  );
}
