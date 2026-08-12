import { useMutation } from "@tanstack/react-query";
import { Lightbulb, Rocket } from "lucide-react";
import { useEffect, useState } from "react";
import { createProject, updatePlainText } from "../../services/projectsService";
import { getErrorMessage } from "../../services/api";
import { PromptEditor } from "../builder/PromptEditor";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { ErrorState } from "../ui/ErrorState";
import type { StageProps } from "./stageTypes";

const tips = [
  "Name the target users and the main jobs they need to complete.",
  "Mention dashboards, CRUD screens, reports, approval flows, or roles that matter.",
  "Add business rules, validation, sample data, and the feeling you want the app to have.",
];

export function PlainTextStage({ project, onProjectChange, onStageChange }: StageProps) {
  const [prompt, setPrompt] = useState(project?.project_data?.plain_text || "");
  const mutation = useMutation({
    mutationFn: async () => {
      if (!prompt.trim()) throw new Error("Enter a project description first.");
      return project?.project_id ? updatePlainText(project.project_id, prompt) : createProject(prompt);
    },
    onSuccess: (nextProject) => {
      onProjectChange(nextProject);
      onStageChange("CLEANED_SPEC");
    },
  });

  useEffect(() => {
    setPrompt(project?.project_data?.plain_text || "");
  }, [project?.project_id]);

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div>
        <PromptEditor value={prompt} onChange={setPrompt} />
        {mutation.isError ? <div className="mt-4"><ErrorState message={getErrorMessage(mutation.error)} /></div> : null}
        <div className="mt-4 flex justify-end">
          <GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()}>
            <Rocket className="h-4 w-4" />
            Start Generating
          </GradientButton>
        </div>
      </div>
      <GlassCard className="p-5">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
          <Lightbulb className="h-4 w-4 text-ember" />
          Strong prompt signals
        </div>
        <div className="space-y-3">
          {tips.map((tip) => (
            <div key={tip} className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-sm leading-6 text-slate-300">
              {tip}
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}

