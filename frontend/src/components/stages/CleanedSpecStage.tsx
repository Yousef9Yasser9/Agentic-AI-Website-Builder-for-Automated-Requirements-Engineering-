import { useMutation } from "@tanstack/react-query";
import { RefreshCw, Sparkles, FileText, Target, Users, Layers, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { generateCleanedSpec } from "../../services/workflowService";
import { getErrorMessage } from "../../services/api";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { JsonViewer } from "../ui/JsonViewer";
import { ErrorState } from "../ui/ErrorState";
import { LoadingState } from "../ui/LoadingState";
import type { StageProps } from "./stageTypes";

export function CleanedSpecStage({ project, onProjectChange }: StageProps) {
  const cleaned = project?.project_data?.cleaned_spec;
  const mutation = useMutation({
    mutationFn: () => generateCleanedSpec(project!.project_id),
    onSuccess: onProjectChange,
  });

  if (!project) return <ErrorState message="Create a project first." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30">
          <Sparkles className="w-6 h-6 text-purple-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">AI Interpretation</h2>
          <p className="text-slate-400 mt-1">
            Refined and structured project specification
          </p>
        </div>
      </div>

      {/* Original vs Cleaned Comparison */}
      {cleaned && (
        <div className="grid lg:grid-cols-2 gap-4">
          <GlassCard className="p-6 border-slate-600/30">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-white">Original Input</h3>
            </div>
            <div className="text-sm text-slate-300 leading-relaxed max-h-40 overflow-y-auto thin-scrollbar">
              {project.project_data?.plain_text}
            </div>
          </GlassCard>
          
          <GlassCard className="p-6 border-purple-500/30 bg-purple-500/5">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-purple-400" />
              <h3 className="font-semibold text-white">AI Enhanced</h3>
              <span className="ml-auto text-xs px-2 py-1 rounded bg-purple-500/20 text-purple-400">
                Structured
              </span>
            </div>
            <div className="text-sm text-slate-200 leading-relaxed max-h-40 overflow-y-auto thin-scrollbar">
              {typeof cleaned.cleaned_prompt === "string" 
                ? cleaned.cleaned_prompt 
                : JSON.stringify(cleaned.cleaned_prompt, null, 2)}
            </div>
          </GlassCard>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()}>
          <Sparkles className="h-4 w-4" />
          {cleaned ? "Regenerate" : "Generate"} Cleaned Spec
        </GradientButton>
        {cleaned && (
          <GradientButton variant="secondary" loading={mutation.isPending} onClick={() => mutation.mutate()}>
            <RefreshCw className="h-4 w-4" />
            Retry
          </GradientButton>
        )}
      </div>
      
      {mutation.isPending && <LoadingState label="Architect model is cleaning the specification" />}
      {mutation.isError && <ErrorState message={getErrorMessage(mutation.error)} />}
      
      {cleaned && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Project Title Card */}
          <GlassCard className="p-8 border-cyan-500/30 bg-cyan-500/5 text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-medium mb-4">
              <Sparkles className="w-3 h-3" />
              AI Generated Title
            </div>
            <h3 className="text-3xl font-bold text-white mb-2">{cleaned.project_title}</h3>
            <p className="text-slate-400">Your project's refined identity</p>
          </GlassCard>
          
          {/* Extracted Information Grid */}
          {cleaned.project_description && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <GlassCard className="p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Target className="w-5 h-5 text-cyan-400" />
                  <h4 className="font-semibold text-white">Description</h4>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {cleaned.project_description}
                </p>
              </GlassCard>
              
              {cleaned.target_users && (
                <GlassCard className="p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Users className="w-5 h-5 text-purple-400" />
                    <h4 className="font-semibold text-white">Target Users</h4>
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {Array.isArray(cleaned.target_users) 
                      ? cleaned.target_users.join(", ")
                      : cleaned.target_users}
                  </p>
                </GlassCard>
              )}
              
              {cleaned.core_features && (
                <GlassCard className="p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Layers className="w-5 h-5 text-green-400" />
                    <h4 className="font-semibold text-white">Core Features</h4>
                  </div>
                  <ul className="text-sm text-slate-300 space-y-1">
                    {Array.isArray(cleaned.core_features) ? (
                      cleaned.core_features.slice(0, 5).map((feature: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <ArrowRight className="w-3 h-3 mt-1 flex-shrink-0 text-green-400" />
                          <span>{feature}</span>
                        </li>
                      ))
                    ) : (
                      <li>{cleaned.core_features}</li>
                    )}
                  </ul>
                </GlassCard>
              )}
            </div>
          )}
          
          {/* Collapsible Raw JSON */}
          <details className="group">
            <summary className="cursor-pointer text-sm font-semibold text-slate-400 hover:text-white transition-colors flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              View Raw JSON Structure
            </summary>
            <div className="mt-4">
              <JsonViewer value={cleaned} />
            </div>
          </details>
        </motion.div>
      )}
    </div>
  );
}

