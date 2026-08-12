import { useMutation } from "@tanstack/react-query";
import { Database, KeyRound, Link2 } from "lucide-react";
import { generateDataModel } from "../../services/workflowService";
import { getErrorMessage } from "../../services/api";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { JsonViewer } from "../ui/JsonViewer";
import { StatusBadge } from "../ui/StatusBadge";
import { ErrorState } from "../ui/ErrorState";
import type { StageProps } from "./stageTypes";

export function DataModelStage({ project, onProjectChange }: StageProps) {
  const model = project?.project_data?.data_model;
  const mutation = useMutation({
    mutationFn: () => generateDataModel(project!.project_id),
    onSuccess: onProjectChange,
  });
  if (!project?.project_data?.architecture) return <ErrorState message="Generate architecture first." />;
  return (
    <div className="space-y-5">
      <GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()}>
        <Database className="h-4 w-4" />
        Generate Data Model
      </GradientButton>
      {mutation.isError ? <ErrorState message={getErrorMessage(mutation.error)} /> : null}
      {model ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {(model.entities || []).map((entity) => (
              <GlassCard key={entity.name} className="overflow-hidden">
                <div className="border-b border-white/10 px-5 py-4">
                  <h3 className="text-base font-semibold text-white">{entity.name}</h3>
                  <p className="mt-1 text-xs text-slate-500">{entity.description || "Database entity"}</p>
                </div>
                <div className="thin-scrollbar overflow-auto">
                  <table className="w-full min-w-[32rem] text-left text-sm">
                    <thead className="bg-white/[0.035] text-xs uppercase tracking-[0.14em] text-slate-500">
                      <tr>
                        <th className="px-4 py-3">Field</th>
                        <th className="px-4 py-3">Type</th>
                        <th className="px-4 py-3">Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(entity.fields || []).map((field) => (
                        <tr key={field.name} className="border-t border-white/8">
                          <td className="px-4 py-3 font-semibold text-slate-100">{field.name}</td>
                          <td className="px-4 py-3 text-slate-400">{field.type}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-2">
                              {field.pk ? <StatusBadge tone="success"><KeyRound className="h-3 w-3" />PK</StatusBadge> : null}
                              {field.fk ? <StatusBadge tone="current"><Link2 className="h-3 w-3" />FK</StatusBadge> : null}
                              {field.unique ? <StatusBadge tone="warning">Unique</StatusBadge> : null}
                              {field.nullable === false ? <StatusBadge tone="neutral">Required</StatusBadge> : null}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            ))}
          </div>
          <GlassCard className="p-5">
            <h3 className="mb-4 text-sm font-semibold text-white">Relationships</h3>
            <div className="grid gap-3 md:grid-cols-2">
              {(model.relationships || []).map((relationship, index) => (
                <div key={`${relationship.from}-${relationship.to}-${index}`} className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-sm">
                  <p className="font-semibold text-slate-100">{relationship.from} to {relationship.to}</p>
                  <p className="mt-1 text-xs text-slate-500">{relationship.type} via {relationship.fk_field}</p>
                </div>
              ))}
            </div>
          </GlassCard>
          <JsonViewer value={model} title="Data Model JSON" />
        </>
      ) : null}
    </div>
  );
}
