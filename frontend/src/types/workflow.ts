import type { LucideIcon } from "lucide-react";
import {
  Binary,
  Blocks,
  Braces,
  Database,
  FileText,
  Layers3,
  ListChecks,
  MonitorPlay,
  PenLine,
  Rocket,
  Sparkles,
} from "lucide-react";
import type { StageKey } from "./project";

export interface StageMeta {
  key: StageKey;
  label: string;
  shortLabel: string;
  description: string;
  doneKey: string;
  icon: LucideIcon;
}

export const WORKFLOW_STAGES: StageMeta[] = [
  {
    key: "PLAIN_TEXT",
    label: "Description",
    shortLabel: "Idea",
    description: "Project idea and product intent.",
    doneKey: "plain_text",
    icon: PenLine,
  },
  {
    key: "CLEANED_SPEC",
    label: "Cleaned Spec",
    shortLabel: "Spec",
    description: "Structured title and refined prompt.",
    doneKey: "cleaned_spec",
    icon: Sparkles,
  },
  {
    key: "REQUIREMENTS",
    label: "Requirements",
    shortLabel: "Reqs",
    description: "Functional and non-functional requirements.",
    doneKey: "requirements",
    icon: ListChecks,
  },
  {
    key: "USER_STORIES",
    label: "User Stories",
    shortLabel: "Stories",
    description: "Traceable stories and acceptance criteria.",
    doneKey: "user_stories",
    icon: FileText,
  },
  {
    key: "ARCHITECTURE",
    label: "Architecture",
    shortLabel: "Arch",
    description: "Stack, pages, modules, and API surface.",
    doneKey: "architecture",
    icon: Blocks,
  },
  {
    key: "DATA_MODEL",
    label: "Data Model",
    shortLabel: "Data",
    description: "Entities, fields, keys, and relationships.",
    doneKey: "data_model",
    icon: Database,
  },
  {
    key: "SRS_DOCUMENTATION",
    label: "SRS Documentation",
    shortLabel: "SRS",
    description: "Markdown software requirements document.",
    doneKey: "srs_document",
    icon: FileText,
  },
  {
    key: "UI_SELECTION",
    label: "UI Selection",
    shortLabel: "UI",
    description: "Framework theme and layout direction.",
    doneKey: "ui_selection",
    icon: Layers3,
  },
  {
    key: "CODE_GENERATION",
    label: "Code Generation",
    shortLabel: "Code",
    description: "Blueprint, manifest, files, and artifacts.",
    doneKey: "tdd_passed",
    icon: Braces,
  },
  {
    key: "BUILD_AND_RUN",
    label: "Build and Run",
    shortLabel: "Build",
    description: "Venv, dependencies, database seed, server launch.",
    doneKey: "build_done",
    icon: Rocket,
  },
  {
    key: "PREVIEW",
    label: "Preview",
    shortLabel: "Live",
    description: "Running app links and server controls.",
    doneKey: "server_pid",
    icon: MonitorPlay,
  },
];

export const stageOrder = WORKFLOW_STAGES.map((stage) => stage.key);

export const methodTone: Record<string, string> = {
  GET: "border-mint/35 bg-mint/10 text-mint",
  POST: "border-electric/35 bg-electric/10 text-electric",
  PUT: "border-ember/35 bg-ember/10 text-ember",
  PATCH: "border-ember/35 bg-ember/10 text-ember",
  DELETE: "border-rose-400/35 bg-rose-400/10 text-rose-300",
};

export const fieldTypeIcon = Binary;
