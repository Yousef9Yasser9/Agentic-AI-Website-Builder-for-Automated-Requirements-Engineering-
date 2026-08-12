import { GenerationTimeline } from "./GenerationTimeline";
import type { GeneratedFile } from "../../types/project";

export function BuildTimeline({ active, done, files }: { active?: boolean; done?: boolean; files?: GeneratedFile[] }) {
  const fileCount = files?.length || 0;

  return (
    <GenerationTimeline
      items={[
        { label: fileCount ? `Validate ${fileCount} generated files` : "Validate generated files", done },
        { label: "Create virtual environment", active: active && !done, done },
        { label: "Install dependencies", active: active && !done, done },
        { label: "Seed database", active: active && !done, done },
        { label: "Start server", active: active && !done, done },
      ]}
    />
  );
}
