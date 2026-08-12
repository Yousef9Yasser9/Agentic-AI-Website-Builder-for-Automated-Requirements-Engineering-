export interface CodeGenerationOptions {
  build_from_scratch: boolean;
  run_tdd: boolean;
  run_refactor: boolean;
  debug_logging: boolean;
}

export interface LogsResponse {
  project_id: string;
  logs: string[];
}

export interface ServerStatus {
  project_id: string;
  running: boolean;
  pid?: number;
  port: number;
  url: string;
  docs_url: string;
  redoc_url: string;
  health_url: string;
  repo_path?: string;
}

