export type StageKey =
  | "PLAIN_TEXT"
  | "CLEANED_SPEC"
  | "REQUIREMENTS"
  | "USER_STORIES"
  | "ARCHITECTURE"
  | "DATA_MODEL"
  | "SRS_DOCUMENTATION"
  | "UI_SELECTION"
  | "CODE_GENERATION"
  | "BUILD_AND_RUN"
  | "PREVIEW";

export interface CleanedSpec {
  project_title?: string;
  project_description?: string;
  cleaned_prompt?: string | Record<string, unknown>;
  target_users?: string | string[];
  core_features?: string | string[];
  [key: string]: unknown;
}

export interface RequirementItem {
  id?: string;
  shall?: string;
  description?: string;
  priority?: string;
  category?: string;
  [key: string]: unknown;
}

export interface Requirements {
  functional?: string[];
  non_functional?: string[];
  nonFunctional?: string[];
  functional_requirements?: RequirementItem[];
  non_functional_requirements?: RequirementItem[];
  [key: string]: unknown;
}

export interface ArchitecturePage {
  name?: string;
  path?: string;
  role_access?: string[];
  [key: string]: unknown;
}

export interface ArchitectureEndpoint {
  method: string;
  path: string;
  desc?: string;
  [key: string]: unknown;
}

export interface Architecture {
  tech_stack?: string | Record<string, unknown>;
  stack?: Record<string, unknown>;
  pages?: ArchitecturePage[];
  modules?: unknown[];
  endpoints?: ArchitectureEndpoint[];
  [key: string]: unknown;
}

export interface DataField {
  name: string;
  type?: string;
  pk?: boolean;
  fk?: boolean;
  unique?: boolean;
  nullable?: boolean;
  [key: string]: unknown;
}

export interface DataEntity {
  name: string;
  description?: string;
  fields?: DataField[];
  [key: string]: unknown;
}

export interface DataRelationship {
  from?: string;
  to?: string;
  type?: string;
  fk_field?: string;
  [key: string]: unknown;
}

export interface DataModel {
  entities?: DataEntity[];
  relationships?: DataRelationship[];
  [key: string]: unknown;
}

export interface UiSelection {
  theme_name?: string;
  layout_name?: string;
  ui_description?: string;
  ui_key?: string;
  layout_key?: string;
  [key: string]: unknown;
}

export interface RecoveryDiagnosis {
  category: "CODE_BUG" | "ARCHITECTURE_MISMATCH" | "DATA_MODEL_GAP" | string;
  confidence?: number;
  reason?: string;
  suggested_stage_to_regenerate?: "ARCHITECTURE" | "DATA_MODEL" | string | null;
  evidence?: string[];
}

export interface UserStory {
  id?: string;
  role?: string;
  story?: string;
  acceptance_criteria?: string[];
  links?: { fr?: string[]; nfr?: string[] };
  [key: string]: unknown;
}

export interface UserStories {
  stories?: UserStory[];
  [key: string]: unknown;
}

export interface GeneratedFile {
  path: string;
  name?: string;
  size?: number;
}

export interface ProjectData {
  plain_text?: string;
  cleaned_spec?: CleanedSpec;
  requirements?: Requirements;
  user_stories?: UserStories;
  architecture?: Architecture;
  data_model?: DataModel;
  srs_document?: string;
  ui_selection?: UiSelection;
  post_analysis?: Record<string, unknown>;
  blueprint?: Record<string, unknown>;
  manifest?: Record<string, unknown>;
  repo_path?: string;
  generated_files?: GeneratedFile[];
  build_done?: boolean;
  build_status?: string;
  recovery_diagnosis?: RecoveryDiagnosis;
  server_pid?: number;
  server_port?: number;
  [key: string]: unknown;
}

export interface ProjectSummary {
  project_id: string;
  project_title: string;
  stage: StageKey | string;
  saved_at?: string;
  server_port?: number;
  user_id?: number | null;
  project_data?: ProjectData;
}

export interface ProjectState extends ProjectSummary {
  project_data: ProjectData;
  checkpoint_path: string;
  stage_done?: boolean;
}

export interface ModelSettings {
  model_architect: string;
  model_coder: string;
  model_ctx_architect: number;
  model_ctx_coder: number;
  model_ctx_reviewer: number;
  model_predict_code_cap: number;
  timeout_requirements_sec: number;
  timeout_architecture_sec: number;
  timeout_data_model_sec: number;
  timeout_srs_sec: number;
  timeout_code_generation_sec: number;
  timeout_refactor_sec: number;
  timeout_post_analysis_sec: number;
  timeout_json_repair_sec: number;
  single_model_mode: boolean;
  enable_llm_refactor: boolean;
  enable_runtime_healing: boolean;
}

export interface OllamaStatus {
  online: boolean;
  models: string[];
  ram_percent?: number;
  ram_warning?: boolean;
  error?: string;
}

export interface SizeReport {
  total?: { size_formatted?: string; size_bytes?: number };
  folders?: Record<string, { size_formatted?: string; size_bytes?: number }>;
  [key: string]: unknown;
}
