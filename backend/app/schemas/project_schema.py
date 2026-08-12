from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelSettings(BaseModel):
    model_architect: str = "llama3.1:8b"
    model_coder: str = "qwen2.5-coder:14b"
    model_ctx_architect: int = 8192
    model_ctx_coder: int = 8192
    model_ctx_reviewer: int = 8192
    model_predict_code_cap: int = 8192
    timeout_requirements_sec: int = 3600
    timeout_architecture_sec: int = 7200
    timeout_data_model_sec: int = 7200
    timeout_srs_sec: int = 3600
    timeout_code_generation_sec: int = 3600
    timeout_refactor_sec: int = 1800
    timeout_post_analysis_sec: int = 3600
    timeout_json_repair_sec: int = 1800
    single_model_mode: bool = False
    enable_llm_refactor: bool = False
    enable_runtime_healing: bool = True


class ProjectCreate(BaseModel):
    plain_text: Optional[str] = None


class ProjectSave(BaseModel):
    project_data: Dict[str, Any] = Field(default_factory=dict)
    stage: str = "PLAIN_TEXT"


class StageUpdate(BaseModel):
    stage: str


class PlainTextRequest(BaseModel):
    plain_text: str


class UiSelectionRequest(BaseModel):
    theme_name: str
    layout_name: str
    bootstrap_css: Optional[str] = None
    layout_key: Optional[str] = None
    theme_vars: Dict[str, Any] = Field(default_factory=dict)
    ui_key: Optional[str] = None
    ui_description: Optional[str] = None
    layout_requirements: List[str] = Field(default_factory=list)


class CodeGenerationRequest(BaseModel):
    build_from_scratch: bool = True
    run_tdd: bool = False
    run_refactor: bool = False
    debug_logging: bool = False


class RegenerateStageRequest(BaseModel):
    stage: str
    reason: str


class CleanupRequest(BaseModel):
    keep_apps: int = 1
    keep_checkpoints: int = 5
