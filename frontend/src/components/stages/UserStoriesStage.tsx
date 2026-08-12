import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckSquare2, Clock3, RefreshCw } from "lucide-react";
import { generateUserStories } from "../../services/workflowService";
import { getErrorMessage } from "../../services/api";
import { GlassCard } from "../ui/GlassCard";
import { GradientButton } from "../ui/GradientButton";
import { JsonViewer } from "../ui/JsonViewer";
import { StatusBadge } from "../ui/StatusBadge";
import { ErrorState } from "../ui/ErrorState";
import type { StageProps } from "./stageTypes";

export function UserStoriesStage({ project, onProjectChange }: StageProps) {
  const storiesObj = project?.project_data?.user_stories;
  const stories = storiesObj?.stories || [];
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const mutation = useMutation({
    mutationFn: () => generateUserStories(project!.project_id),
    onSuccess: onProjectChange,
  });

  useEffect(() => {
    if (!mutation.isPending) {
      setElapsedSeconds(0);
      return;
    }

    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [mutation.isPending]);

  const elapsedLabel = `${Math.floor(elapsedSeconds / 60)}:${String(elapsedSeconds % 60).padStart(2, "0")}`;

  if (!project?.project_data?.requirements) return <ErrorState message="Generate requirements first." />;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()}>
          <CheckSquare2 className="h-4 w-4" />
          Generate User Stories
        </GradientButton>
        {stories.length ? (
          <GradientButton variant="secondary" loading={mutation.isPending} onClick={() => mutation.mutate()}>
            <RefreshCw className="h-4 w-4" />
            Regenerate
          </GradientButton>
        ) : null}
      </div>
      {mutation.isPending ? (
        <GlassCard className="flex items-start gap-3 p-4">
          <Clock3 className="mt-0.5 h-5 w-5 flex-none text-blue-300" />
          <div>
            <p className="text-sm font-semibold text-white">
              Ollama is generating user stories - {elapsedLabel}
            </p>
            <p className="mt-1 text-sm text-slate-400">
              {elapsedSeconds >= 180
                ? "This is slower than expected. The backend will stop the request automatically if Ollama cannot finish."
                : "The result is generated once, validated, and saved automatically."}
            </p>
          </div>
        </GlassCard>
      ) : null}
      {mutation.isError ? <ErrorState message={getErrorMessage(mutation.error)} /> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {stories.map((story) => (
          <GlassCard key={story.id || story.story} className="p-5">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <StatusBadge tone="current">{story.id || "Story"}</StatusBadge>
              {story.role ? <StatusBadge tone="neutral">{story.role}</StatusBadge> : null}
            </div>
            <p className="text-sm font-semibold leading-6 text-white">{story.story}</p>
            <div className="mt-4 space-y-2">
              {(story.acceptance_criteria || []).map((item: string) => (
                <div key={item} className="flex gap-2 text-sm text-slate-300">
                  <CheckSquare2 className="mt-0.5 h-4 w-4 flex-none text-mint" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {(story.links?.fr || []).map((id: string) => <StatusBadge key={id} tone="success">{id}</StatusBadge>)}
              {(story.links?.nfr || []).map((id: string) => <StatusBadge key={id} tone="warning">{id}</StatusBadge>)}
            </div>
          </GlassCard>
        ))}
      </div>
      {storiesObj ? <JsonViewer value={storiesObj} title="Stories JSON" /> : null}
    </div>
  );
}
