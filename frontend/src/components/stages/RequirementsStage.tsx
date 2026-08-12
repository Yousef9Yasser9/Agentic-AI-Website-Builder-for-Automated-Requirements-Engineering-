import { useMutation } from "@tanstack/react-query";
import { Download, ListChecks, Shield, Zap, CheckCircle, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { artifactUrl } from "../../services/projectsService";
import { generateRequirements } from "../../services/workflowService";
import { getErrorMessage } from "../../services/api";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { JsonViewer } from "../ui/JsonViewer";
import { StatusBadge } from "../ui/StatusBadge";
import { ErrorState } from "../ui/ErrorState";
import type { StageProps } from "./stageTypes";
import type { RequirementItem } from "../../types/project";

function RequirementColumn({ title, items, color, icon: Icon }: { title: string; items: RequirementItem[]; color: string; icon: LucideIcon }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2 rounded-lg bg-gradient-to-br ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      <div className="space-y-3">
        {items.map((item, index) => {
          const shallText = item.shall || item.description || "Requirement";
          return (
            <motion.details
              key={item.id || index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="group rounded-lg border border-white/10 bg-white/[0.04] hover:border-cyan-500/30 hover:bg-white/[0.06] transition-all"
            >
              <summary className="cursor-pointer p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <StatusBadge tone="current" className="text-xs">{item.id || "REQ"}</StatusBadge>
                      {item.priority && (
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          item.priority === "P0" || item.priority === "High" ? "bg-red-500/20 text-red-400" :
                          item.priority === "P1" || item.priority === "Medium" ? "bg-yellow-500/20 text-yellow-400" :
                          "bg-green-500/20 text-green-400"
                        }`}>
                          {item.priority}
                        </span>
                      )}
                      {item.category && (
                        <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-400">
                          {item.category}
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-slate-200">{shallText}</p>
                  </div>
                </div>
              </summary>
              <div className="px-4 pb-4 pt-2 border-t border-white/5 mt-2">
                <pre className="thin-scrollbar overflow-auto rounded-md bg-slate-950/70 p-3 text-xs text-slate-300">{JSON.stringify(item, null, 2)}</pre>
              </div>
            </motion.details>
          );
        })}
      </div>
    </div>
  );
}

export function RequirementsStage({ project, onProjectChange }: StageProps) {
  const reqs = project?.project_data?.requirements;
  const mutation = useMutation({
    mutationFn: () => generateRequirements(project!.project_id),
    onSuccess: onProjectChange,
  });
  
  if (!project?.project_data?.cleaned_spec) {
    return <ErrorState message="Generate the cleaned specification first." />;
  }
  
  const frs = reqs?.functional_requirements || [];
  const nfrs = reqs?.non_functional_requirements || [];
  const total = frs.length + nfrs.length;
  
  // Count priorities
  const highPriority = [...frs, ...nfrs].filter(r => r.priority === "P0" || r.priority === "High").length;
  const securityReqs = [...frs, ...nfrs].filter(r => r.category?.toLowerCase().includes("security")).length;
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30">
            <ListChecks className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Requirements Extraction</h2>
            <p className="text-slate-400 mt-1">
              AI-generated functional and non-functional requirements
            </p>
          </div>
        </div>
        
        {reqs && (
          <GlassCard className="p-6 border-cyan-500/30 bg-cyan-500/5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-white mb-1">{total}</div>
                <div className="text-xs text-slate-400 uppercase">Total Requirements</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-cyan-400 mb-1">{frs.length}</div>
                <div className="text-xs text-slate-400 uppercase">Functional</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-purple-400 mb-1">{nfrs.length}</div>
                <div className="text-xs text-slate-400 uppercase">Non-Functional</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-red-400 mb-1">{highPriority}</div>
                <div className="text-xs text-slate-400 uppercase">High Priority</div>
              </div>
            </div>
          </GlassCard>
        )}
      </div>
      
      {/* Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()}>
          <ListChecks className="h-4 w-4" />
          {reqs ? "Regenerate" : "Generate"} Requirements
        </GradientButton>
        {reqs && (
          <a
            href={artifactUrl(project.project_id, "requirements")}
            className="inline-flex min-h-10 items-center gap-2 rounded-md border border-white/14 bg-white/8 px-4 py-2 text-sm font-semibold text-slate-100 hover:bg-white/12 transition-colors"
          >
            <Download className="h-4 w-4" />
            Download JSON
          </a>
        )}
      </div>
      
      {mutation.isError && <ErrorState message={getErrorMessage(mutation.error)} />}
      
      {reqs && (
        <>
          <div className="grid gap-6 lg:grid-cols-2">
            <GlassCard className="p-6 border-cyan-500/30 bg-cyan-500/5">
              <RequirementColumn
                title={`Functional Requirements (${frs.length})`}
                items={frs}
                color="from-cyan-500 to-blue-500"
                icon={Zap}
              />
            </GlassCard>
            <GlassCard className="p-6 border-purple-500/30 bg-purple-500/5">
              <RequirementColumn
                title={`Non-Functional Requirements (${nfrs.length})`}
                items={nfrs}
                color="from-purple-500 to-pink-500"
                icon={Shield}
              />
            </GlassCard>
          </div>
          
          <details className="group">
            <summary className="cursor-pointer text-sm font-semibold text-slate-400 hover:text-white transition-colors">
              View Raw JSON
            </summary>
            <div className="mt-4">
              <JsonViewer value={reqs} title="Requirements JSON" />
            </div>
          </details>
        </>
      )}
    </div>
  );
}
