import { useMutation } from "@tanstack/react-query";
import { Download, FileText } from "lucide-react";
import { artifactUrl } from "../../services/projectsService";
import { generateSrs } from "../../services/workflowService";
import { getErrorMessage } from "../../services/api";
import { GradientButton } from "../ui/GradientButton";
import { MarkdownPreview } from "../ui/MarkdownPreview";
import { JsonViewer } from "../ui/JsonViewer";
import { ErrorState } from "../ui/ErrorState";
import type { StageProps } from "./stageTypes";

export function SrsDocumentationStage({ project, onProjectChange }: StageProps) {
  const markdown = project?.project_data?.srs_document;
  const mutation = useMutation({
    mutationFn: () => generateSrs(project!.project_id),
    onSuccess: onProjectChange,
  });
  if (!project?.project_data?.data_model) return <ErrorState message="Generate the data model first." />;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <GradientButton loading={mutation.isPending} onClick={() => mutation.mutate()}>
          <FileText className="h-4 w-4" />
          Generate SRS
        </GradientButton>
        {markdown ? (
          <a href={artifactUrl(project.project_id, "srs")} className="inline-flex min-h-10 items-center gap-2 rounded-md border border-white/14 bg-white/8 px-4 py-2 text-sm font-semibold text-slate-100">
            <Download className="h-4 w-4" />
            Download Markdown
          </a>
        ) : null}
      </div>
      {mutation.isError ? <ErrorState message={getErrorMessage(mutation.error)} /> : null}
      {markdown ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_24rem]">
          <MarkdownPreview markdown={markdown} />
          <JsonViewer value={{ srs_document: markdown }} title="SRS Payload" />
        </div>
      ) : null}
    </div>
  );
}

