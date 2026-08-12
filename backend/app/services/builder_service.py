from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil
import requests

ROOT_DIR = Path(__file__).resolve().parents[3]
BUILDER_DIR = ROOT_DIR / "builder"
LOCAL_TMP = ROOT_DIR / ".tmp"
SETTINGS_PATH = LOCAL_TMP / "model_settings.json"

for path in (ROOT_DIR, BUILDER_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from builder.import_fixes import repair_deterministic_backend_layout

repair_deterministic_backend_layout(ROOT_DIR)

from blueprint_generator import generate_file_manifest, generate_project_blueprint
from checkpoint_manager import (
    CHECKPOINTS_DIR,
    delete_checkpoint,
    get_checkpoint_owner,
    list_projects,
    load_checkpoint,
    save_checkpoint,
    save_checkpoint_history,
)
from cleanup_manager import full_cleanup, get_project_size_report
from generated_apps.generator.repo_generator import generate_repo
from ollama_client import ollama_chat, parse_json_with_fix
from prompts import (
    ANALYSIS_SYSTEM,
    ARCHITECTURE_SYSTEM,
    CLEAN_SPEC_SYSTEM,
    DATA_MODEL_SYSTEM,
    REQUIREMENTS_SYSTEM,
    SRS_SYSTEM,
    USER_STORIES_SYSTEM,
)


STAGES: List[str] = [
    "PLAIN_TEXT",
    "CLEANED_SPEC",
    "REQUIREMENTS",
    "USER_STORIES",
    "ARCHITECTURE",
    "DATA_MODEL",
    "SRS_DOCUMENTATION",
    "UI_SELECTION",
    "CODE_GENERATION",
    "BUILD_AND_RUN",
    "PREVIEW",
]

STAGE_DONE_KEY: Dict[str, str] = {
    "PLAIN_TEXT": "plain_text",
    "CLEANED_SPEC": "cleaned_spec",
    "REQUIREMENTS": "requirements",
    "USER_STORIES": "user_stories",
    "ARCHITECTURE": "architecture",
    "DATA_MODEL": "data_model",
    "SRS_DOCUMENTATION": "srs_document",
    "UI_SELECTION": "ui_selection",
    "CODE_GENERATION": "tdd_passed",
    "BUILD_AND_RUN": "build_done",
    "PREVIEW": "server_pid",
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "model_architect": "llama3.1:8b",
    "model_coder": "qwen2.5-coder:14b",
    "model_ctx_architect": 8192,
    "model_ctx_coder": 8192,
    "model_ctx_reviewer": 8192,
    "model_predict_code_cap": 8192,
    "timeout_requirements_sec": 3600,
    "timeout_architecture_sec": 7200,
    "timeout_data_model_sec": 7200,
    "timeout_srs_sec": 3600,
    "timeout_code_generation_sec": 3600,
    "timeout_refactor_sec": 1800,
    "timeout_post_analysis_sec": 3600,
    "timeout_json_repair_sec": 1800,
    "single_model_mode": False,
    "enable_llm_refactor": False,
    "enable_runtime_healing": True,
}

PROJECT_LOGS: Dict[str, List[str]] = {}
SERVER_PROCESSES: Dict[str, subprocess.Popen] = {}
AUTO_RECOVERY_STAGES = {"ARCHITECTURE", "DATA_MODEL"}
MAX_AUTO_RECOVERY_ATTEMPTS = 2


def _save_checkpoint(
    project_id: str,
    project_data: dict,
    stage: str,
    user_id: int | None = None,
) -> Path:
    path = save_checkpoint(project_id, project_data, stage, user_id=user_id)
    save_checkpoint_history(project_id, project_data, stage)
    return path


def _validate_project_id(project_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", project_id or ""):
        raise ValueError("Invalid project id")
    return project_id


def _subprocess_env(*, cwd: Path | None = None, extra: dict | None = None) -> dict:
    tmp_root = Path(cwd) / ".tmp" if cwd else LOCAL_TMP
    tmp_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["TMP"] = str(tmp_root)
    env["TEMP"] = str(tmp_root)
    env["TMPDIR"] = str(tmp_root)
    if extra:
        env.update(extra)
    return env


def append_log(project_id: str, line: str) -> None:
    PROJECT_LOGS.setdefault(project_id, []).append(str(line))
    if len(PROJECT_LOGS[project_id]) > 500:
        PROJECT_LOGS[project_id] = PROJECT_LOGS[project_id][-500:]


def _clear_downstream_stage_data(project_data: dict, stage: str) -> None:
    if stage not in STAGES:
        return
    downstream = STAGES[STAGES.index(stage) + 1 :]
    for downstream_stage in downstream:
        key = STAGE_DONE_KEY.get(downstream_stage)
        if key:
            project_data.pop(key, None)
    extra_by_stage = {
        "REQUIREMENTS": ["requirements"],
        "USER_STORIES": ["user_stories"],
        "ARCHITECTURE": ["architecture"],
        "DATA_MODEL": ["data_model"],
        "SRS_DOCUMENTATION": ["srs_document"],
        "UI_SELECTION": ["ui_selection"],
        "CODE_GENERATION": [
            "repo_path",
            "generated_files",
            "blueprint",
            "file_manifest",
            "generation_options",
            "codegen_context",
            "validation_issues",
            "tdd_passed",
            "tdd_error",
            "tdd_history",
            "tdd_skipped",
            "recovery_diagnosis",
        ],
        "BUILD_AND_RUN": ["build_done", "build_status", "build_error", "build_log_tail", "seed_ok"],
        "PREVIEW": ["server_pid", "server_port"],
    }
    for downstream_stage in downstream:
        for key in extra_by_stage.get(downstream_stage, []):
            project_data.pop(key, None)


def get_logs(project_id: str) -> Dict[str, Any]:
    _validate_project_id(project_id)
    return {"project_id": project_id, "logs": PROJECT_LOGS.get(project_id, [])}


def get_project_port(project_id: str) -> int:
    _validate_project_id(project_id)
    value = int(hashlib.md5(project_id.encode("utf-8")).hexdigest(), 16)
    return 8100 + (value % 900)


def load_settings() -> Dict[str, Any]:
    LOCAL_TMP.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
        return dict(DEFAULT_SETTINGS)
    try:
        loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        loaded = {}
    merged = {**DEFAULT_SETTINGS, **loaded}
    merged["model_ctx_architect"] = min(int(merged.get("model_ctx_architect") or 8192), 16384)
    merged["model_ctx_reviewer"] = min(int(merged.get("model_ctx_reviewer") or 8192), 16384)
    merged["model_ctx_coder"] = min(int(merged.get("model_ctx_coder") or 8192), 16384)
    merged["model_predict_code_cap"] = min(max(int(merged.get("model_predict_code_cap") or 8192), 1200), 16384)
    for key, default, ceiling in (
        ("timeout_requirements_sec", 3600, 10800),
        ("timeout_architecture_sec", 7200, 14400),
        ("timeout_data_model_sec", 7200, 14400),
        ("timeout_srs_sec", 3600, 10800),
        ("timeout_code_generation_sec", 3600, 14400),
        ("timeout_refactor_sec", 1800, 10800),
        ("timeout_post_analysis_sec", 3600, 10800),
        ("timeout_json_repair_sec", 1800, 7200),
    ):
        merged[key] = min(max(int(merged.get(key) or default), 60), ceiling)
    return merged


def save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    merged = {**DEFAULT_SETTINGS, **settings}
    LOCAL_TMP.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def ask_llm(
    system: str,
    user: str,
    num_predict: int = 4096,
    model: str | None = None,
    num_ctx: int | None = None,
    response_format: str | None = None,
    temperature: float = 0.1,
    timeout_sec: int | None = 900,
    retries: int = 5,
) -> str:
    settings = load_settings()
    chosen_model = model or settings["model_coder"]
    chosen_ctx = num_ctx or settings["model_ctx_coder"]
    try:
        return ollama_chat(
            model=chosen_model,
            system=system,
            user=user,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=chosen_ctx,
            num_gpu=999,
            timeout_sec=timeout_sec,
            retries=retries,
            response_format=response_format,
        )
    except Exception as exc:
        text = str(exc)
        if "model" in text.lower() and "not found" in text.lower():
            raise RuntimeError(
                f"Ollama model '{chosen_model}' is not installed. Use a model from ollama list or pull it first."
            ) from exc
        if "11434" in text or "Connection" in text:
            raise RuntimeError("Ollama is offline. Start Ollama and try again.") from exc
        raise


def require_keys(payload: dict, keys: list[str], stage_name: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{stage_name}: Missing keys: {missing}")


def safe_llm_json(
    stage_name: str,
    system: str,
    payload_obj: dict,
    temperature: float = 0.2,
    num_predict: int = 4096,
    model: str | None = None,
    num_ctx: int | None = None,
    require_keys_list: Optional[List[str]] = None,
    timeout_sec: int = 900,
    retries: int = 4,
    json_repair_timeout_sec: int | None = None,
    json_repair_retries: int = 1,
    json_repair_num_predict: int = 2000,
    json_validation_retries: int = 1,
) -> dict:
    settings = load_settings()
    chosen_model = model or settings["model_architect"]
    chosen_ctx = num_ctx or settings["model_ctx_architect"]
    last_error: Exception | None = None
    user_payload = json.dumps(payload_obj, ensure_ascii=False)
    for attempt in range(max(0, json_validation_retries) + 1):
        retry_note = ""
        if attempt:
            retry_note = (
                "\n\nIMPORTANT RETRY: The previous response was invalid, incomplete, "
                "or missing required keys. Return one COMPLETE valid JSON object only. "
                "Do not stop early. Do not add markdown."
            )
        raw = ollama_chat(
            model=chosen_model,
            system=system + retry_note,
            user=user_payload,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=chosen_ctx,
            num_gpu=999,
            response_format="json",
            timeout_sec=timeout_sec,
            retries=retries,
        )
        try:
            parsed = parse_json_with_fix(
                chosen_model,
                raw,
                timeout_sec=json_repair_timeout_sec or timeout_sec,
                require_keys=require_keys_list,
                repair_retries=json_repair_retries,
                repair_num_predict=json_repair_num_predict,
            )
            if require_keys_list:
                require_keys(parsed, require_keys_list, stage_name)
            return parsed
        except Exception as exc:
            last_error = exc
    raise last_error or ValueError(f"{stage_name}: model did not return valid JSON")


def project_summary(project_id: str, project_data: dict, stage: str) -> Dict[str, Any]:
    title = (project_data.get("cleaned_spec") or {}).get("project_title") or project_data.get("plain_text", "")[:60] or project_id
    checkpoint = CHECKPOINTS_DIR / project_id / "checkpoint.json"
    return {
        "project_id": project_id,
        "project_title": title,
        "stage": stage,
        "project_data": project_data,
        "checkpoint_path": str(checkpoint),
        "server_port": get_project_port(project_id),
        "stage_done": stage_is_done(project_data, stage),
        "user_id": get_checkpoint_owner(project_id),
    }


def assert_project_access(project_id: str, user_id: int, is_admin: bool) -> None:
    _validate_project_id(project_id)
    owner = get_checkpoint_owner(project_id)
    if is_admin:
        return
    if owner is None:
        return
    if owner != user_id:
        raise PermissionError("You do not have access to this project.")


def _stage_completion_percent(stage: str) -> int:
    if stage not in STAGES:
        return 0
    return int(round((STAGES.index(stage) + 1) / len(STAGES) * 100))


def is_server_running(project_id: str) -> bool:
    proc = SERVER_PROCESSES.get(project_id)
    return bool(proc and proc.poll() is None)


def stage_is_done(project_data: dict, stage: str) -> bool:
    key = STAGE_DONE_KEY.get(stage)
    return bool(key and project_data.get(key))


def create_project(plain_text: str | None = None, user_id: int | None = None) -> Dict[str, Any]:
    project_id = str(uuid.uuid4())[:8]
    data: Dict[str, Any] = {}
    stage = "PLAIN_TEXT"
    if plain_text and plain_text.strip():
        data["plain_text"] = plain_text.strip()
    _save_checkpoint(project_id, data, stage, user_id=user_id)
    append_log(project_id, f"[project] Created project {project_id}")
    return project_summary(project_id, data, stage)


def get_project(project_id: str, user_id: int | None = None, is_admin: bool = False) -> Dict[str, Any]:
    _validate_project_id(project_id)
    if user_id is not None:
        assert_project_access(project_id, user_id, is_admin)
    data, stage = load_checkpoint(project_id)
    return project_summary(project_id, data, stage)


def list_project_summaries(user_id: int | None = None, is_admin: bool = False) -> List[dict]:
    projects = list_projects()
    if not is_admin and user_id is not None:
        projects = [
            project
            for project in projects
            if project.get("user_id") is None or project.get("user_id") == user_id
        ]
    for project in projects:
        project["server_port"] = get_project_port(project["project_id"])
    return projects


def list_all_project_summaries() -> List[dict]:
    return list_project_summaries(is_admin=True)


def list_all_project_summaries_enriched() -> List[dict]:
    enriched: List[dict] = []
    for summary in list_all_project_summaries():
        project_id = summary["project_id"]
        try:
            full = get_project(project_id)
        except Exception:
            continue
        data = full.get("project_data") or {}
        enriched.append(
            {
                **summary,
                "completion_percent": _stage_completion_percent(summary.get("stage", "PLAIN_TEXT")),
                "generated_app_status": "running"
                if is_server_running(project_id)
                else ("built" if data.get("repo_path") else "none"),
                "owner_user_id": summary.get("user_id"),
            }
        )
    return enriched


def _clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip(" -:\t\r\n"))


def _title_from_prompt(plain_text: str) -> str:
    first = next((line.strip() for line in plain_text.splitlines() if line.strip()), "")
    first = re.sub(r"^(build|create|make|develop)\s+(an?\s+)?", "", first, flags=re.IGNORECASE)
    first = first.strip(" .:-")
    if not first:
        return "Generated Web App"
    return " ".join(word[:1].upper() + word[1:] for word in re.split(r"\s+", first))


def _count_project_briefs(plain_text: str) -> int:
    return len(re.findall(r"(?im)^\s*(build|create|develop)\s+(an?\s+)?[a-z0-9]", plain_text or ""))


def _extract_sections(plain_text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current = ""
    for raw_line in plain_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = re.match(r"^([A-Za-z][A-Za-z ]+):\s*$", line)
        if heading:
            current = heading.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections.setdefault(current, []).append(line)
    return sections


def _parse_roles(lines: List[str]) -> List[str]:
    roles: List[str] = []
    for line in lines:
        match = re.match(r"^[-*]\s*([^:]+):\s*(.+)$", line)
        if match:
            role = _clean_label(match.group(1))
            desc = _clean_label(match.group(2))
            roles.append(f"{role}: {desc}")
            continue
        value = _clean_label(re.sub(r"^[-*]\s*", "", line))
        if value:
            roles.append(value)
    return roles or ["User: can use the generated application", "Admin: can manage the application"]


def _parse_entities(lines: List[str]) -> Dict[str, List[str]]:
    entities: Dict[str, List[str]] = {}
    for line in lines:
        match = re.match(r"^[-*]\s*([^:]+):\s*(.+)$", line)
        if not match:
            values = [
                _clean_label(item)
                for item in re.split(r",|\band\b", re.sub(r"^[-*]\s*", "", line))
                if _clean_label(item)
            ]
            for value in values:
                if value and re.fullmatch(r"[A-Za-z][A-Za-z0-9 ]*", value):
                    entities.setdefault(value, [])
            continue
        name = _clean_label(match.group(1))
        fields = [
            _clean_label(item)
            for item in re.split(r",|\band\b", match.group(2))
            if _clean_label(item)
        ]
        if name:
            entities[name] = fields
    return entities


def _snake_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(value or ""))
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _pascal_case(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(value or "")))


def _field_type(field_name: str) -> str:
    name = _snake_case(field_name)
    if name in {"id"} or name.endswith("_id"):
        return "uuid"
    if any(token in name for token in ("amount", "price", "fee", "cost", "total")):
        return "decimal"
    if name in {"date", "appointment_date"}:
        return "date"
    if name in {"time", "appointment_time", "available_days", "method", "status", "role", "phone"}:
        return "string"
    if any(token in name for token in ("note", "reason", "description", "bio")):
        return "text"
    if name.endswith("_at"):
        return "datetime"
    return "string"


def _ensure_field(fields: List[dict], name: str, field_type: str, **extra: Any) -> None:
    if any(field.get("name") == name for field in fields):
        return
    fields.append({"name": name, "type": field_type, **extra})


def _login_role_names(cleaned_prompt: Dict[str, Any]) -> set[str]:
    roles = set()
    features = cleaned_prompt.get("Features")
    if isinstance(features, dict):
        roles.update(_snake_case(role) for role in features.keys())
    for role_line in cleaned_prompt.get("Roles") or []:
        role, _, _desc = str(role_line).partition(":")
        if role:
            roles.add(_snake_case(role))
    return {role for role in roles if role and role not in {"user"}}


def _relationship_target(entity_name: str, field_name: str, entity_names: set[str], login_roles: set[str] | None = None) -> str | None:
    field = _snake_case(field_name)
    role_names = login_roles or set()
    if field in {"user", "user_id", "patient", "patient_id"}:
        return "User"
    if field in {"doctor", "doctor_id"} and "DoctorProfile" in entity_names:
        return "DoctorProfile"
    if field in {"specialty", "specialty_id"} and "Specialty" in entity_names:
        return "Specialty"
    if field in {"appointment", "appointment_id"} and "Appointment" in entity_names:
        return "Appointment"
    base = field[:-3] if field.endswith("_id") else field
    if base in role_names:
        return "User"
    for candidate in entity_names:
        if _snake_case(candidate) == base:
            return candidate
    return None


def _role_feature_map(roles: List[str]) -> Dict[str, List[str]]:
    features: Dict[str, List[str]] = {}
    for role_line in roles:
        role, _, desc = role_line.partition(":")
        role_name = _clean_label(role) or "User"
        actions = [
            _clean_label(action)
            for action in re.split(r",|\band\b", desc)
            if _clean_label(action)
        ]
        features[role_name] = actions or [desc.strip()] if desc else ["Use assigned workspace"]
    return features


def _domain_theme(title: str, plain_text: str) -> str:
    text = f"{title} {plain_text}".lower()
    if any(word in text for word in ("clinic", "doctor", "patient", "appointment", "medical")):
        return "Healthcare-focused UI with calm sapphire and teal colors, Inter headings, Manrope body text, clear appointment cards, schedule tables, and reassuring patient-friendly spacing."
    if any(word in text for word in ("hotel", "room", "guest", "check-in", "check out", "checkout", "receptionist", "stay history")):
        return "Hospitality reservation UI with polished room cards, warm concierge accents, availability calendars, guest stay timelines, and receptionist operations panels."
    if any(word in text for word in ("restaurant", "menu", "dining", "pickup", "orderitem", "kitchen")):
        return "Premium restaurant UI with warm amber, cream, and deep charcoal colors, Playfair Display headings, Inter body text, menu cards, reservation forms, and staff operations panels."
    if any(word in text for word in ("real estate", "property", "tenant", "agent", "rental", "viewing")):
        return "Real estate product UI with polished property cards, map-like spatial sections, emerald and slate accents, elegant listing details, and application-flow forms."
    if any(word in text for word in ("school", "student", "teacher", "course", "assignment", "grade")):
        return "Education platform UI with bright indigo and sky accents, friendly learning cards, course progress sections, assignment queues, and teacher grading workspaces."
    if any(word in text for word in ("project management", "kanban", "task", "team", "manager", "activitylog")):
        return "Modern productivity UI with kanban boards, crisp task cards, violet-blue accents, compact collaboration panels, and manager progress dashboards."
    if any(word in text for word in ("finance", "expense", "approval", "receipt", "reimbursement", "policy")):
        return "Polished finance operations UI with navy, mint, and white surfaces, receipt upload flows, approval queues, reimbursement status cards, and executive dashboards."
    if any(word in text for word in ("store", "shop", "commerce", "product", "order")):
        return "Commerce UI with energetic blue-purple accents, clean product cards, strong checkout actions, and admin inventory views."
    return "Premium SaaS UI with clear role-based navigation, responsive cards, focused forms, and a polished dashboard layout."


def list_generated_apps_admin() -> List[dict]:
    apps: List[dict] = []
    for summary in list_all_project_summaries_enriched():
        data = {}
        try:
            full = get_project(summary["project_id"])
            data = full.get("project_data") or {}
        except Exception:
            pass
        if not data.get("repo_path"):
            continue
        apps.append(
            {
                "project_id": summary["project_id"],
                "app_name": summary.get("project_title") or summary["project_id"],
                "owner_user_id": summary.get("user_id"),
                "stack": data.get("architecture", {}).get("tech_stack", "FastAPI + SQLite"),
                "folder_path": data.get("repo_path"),
                "server_port": summary.get("server_port"),
                "running": is_server_running(summary["project_id"]),
            }
        )
    return apps


def get_system_health() -> Dict[str, Any]:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(ROOT_DIR))
    size = size_report()
    ollama = ollama_status()
    warnings: List[str] = []
    if not ollama.get("online"):
        warnings.append("Ollama is offline")
    if mem.percent >= 80:
        warnings.append("High RAM usage")
    if disk.percent >= 90:
        warnings.append("Low disk space")
    return {
        "ollama": ollama,
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "checkpoints_size_mb": round((size.get("checkpoints") or {}).get("size_bytes", 0) / (1024 * 1024), 2),
        "generated_apps_size_mb": round((size.get("generated_apps") or {}).get("size_bytes", 0) / (1024 * 1024), 2),
        "warnings": warnings,
    }


def get_all_logs() -> Dict[str, Any]:
    entries: List[dict] = []
    for project_id, lines in PROJECT_LOGS.items():
        for line in lines[-20:]:
            entries.append({"project_id": project_id, "message": line, "type": "builder"})
    entries.sort(key=lambda item: item["message"], reverse=True)
    return {"logs": entries[:200]}


def save_project(project_id: str, project_data: dict, stage: str) -> Dict[str, Any]:
    _validate_project_id(project_id)
    if stage not in STAGES and stage != "POST_ANALYSIS":
        raise ValueError(f"Unknown stage: {stage}")
    _save_checkpoint(project_id, project_data, stage)
    append_log(project_id, f"[checkpoint] Saved {stage}")
    return project_summary(project_id, project_data, stage)


def delete_project(project_id: str) -> Dict[str, Any]:
    stop_server(project_id)
    delete_checkpoint(project_id)
    PROJECT_LOGS.pop(project_id, None)
    return {"deleted": True, "project_id": project_id}


def update_plain_text(project_id: str, plain_text: str) -> Dict[str, Any]:
    if not plain_text.strip():
        raise ValueError("Project description is required.")
    data, _ = load_checkpoint(project_id)
    data["plain_text"] = plain_text.strip()
    _clear_downstream_stage_data(data, "PLAIN_TEXT")
    _save_checkpoint(project_id, data, "PLAIN_TEXT")
    append_log(project_id, "[plain-text] Description saved")
    return project_summary(project_id, data, "PLAIN_TEXT")


def update_stage(project_id: str, stage: str) -> Dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    data, _ = load_checkpoint(project_id)
    _save_checkpoint(project_id, data, stage)
    append_log(project_id, f"[stage] Moved to {stage}")
    return project_summary(project_id, data, stage)


def generate_cleaned_spec(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    plain_text = data.get("plain_text", "")
    if not plain_text:
        raise ValueError("No plain text description found.")
    if _count_project_briefs(plain_text) > 1:
        raise ValueError(
            "Multiple app briefs detected. Create one builder project per prompt so roles, entities, and forbidden modules do not mix."
        )
    settings = load_settings()
    append_log(project_id, f"[cleaned-spec] Asking Ollama model {settings['model_architect']} to interpret the prompt")
    cleaned = safe_llm_json(
        "CLEANED_SPEC",
        CLEAN_SPEC_SYSTEM,
        {"plain_text": plain_text},
        temperature=0.2,
        num_predict=4096,
        model=settings["model_architect"],
        num_ctx=settings["model_ctx_architect"],
        require_keys_list=["project_title", "cleaned_prompt"],
        timeout_sec=settings["timeout_requirements_sec"],
        retries=1,
        json_repair_timeout_sec=settings["timeout_json_repair_sec"],
        json_repair_retries=2,
        json_repair_num_predict=4096,
        json_validation_retries=1,
    )
    if not isinstance(cleaned.get("cleaned_prompt"), dict):
        append_log(project_id, "[cleaned-spec:error] Ollama returned an invalid cleaned_prompt")
        raise ValueError("CLEANED_SPEC: Ollama returned an invalid cleaned_prompt. Retry with the architect model.")
    cleaned_prompt = cleaned.get("cleaned_prompt") or {}
    if not cleaned_prompt.get("Roles") or not cleaned_prompt.get("Data"):
        append_log(project_id, "[cleaned-spec:error] Ollama missed roles or entities")
        raise ValueError("CLEANED_SPEC: Ollama missed roles or entities. Make the prompt explicit and retry.")
    data["cleaned_spec"] = cleaned
    _clear_downstream_stage_data(data, "CLEANED_SPEC")
    _save_checkpoint(project_id, data, "CLEANED_SPEC")
    append_log(project_id, "[cleaned-spec] Complete")
    return project_summary(project_id, data, "CLEANED_SPEC")


def generate_requirements(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    cleaned = data.get("cleaned_spec")
    if not cleaned:
        raise ValueError("Generate cleaned spec first.")
    settings = load_settings()
    append_log(project_id, f"[requirements] Asking Ollama model {settings['model_architect']} for FR/NFR requirements")
    reqs = safe_llm_json(
        "REQUIREMENTS",
        REQUIREMENTS_SYSTEM,
        {"cleaned_spec": cleaned},
        temperature=0.2,
        num_predict=4096,
        require_keys_list=["project_title", "functional_requirements", "non_functional_requirements"],
        timeout_sec=settings["timeout_requirements_sec"],
        retries=1,
        json_repair_timeout_sec=settings["timeout_json_repair_sec"],
        json_repair_retries=2,
        json_repair_num_predict=4096,
        json_validation_retries=1,
    )
    if not reqs.get("functional_requirements"):
        raise ValueError("REQUIREMENTS: functional_requirements is empty")
    if not reqs.get("non_functional_requirements"):
        raise ValueError("REQUIREMENTS: non_functional_requirements is empty")
    data["requirements"] = reqs
    _clear_downstream_stage_data(data, "REQUIREMENTS")
    project_dir = CHECKPOINTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "requirements.json").write_text(json.dumps(reqs, indent=2, ensure_ascii=False), encoding="utf-8")
    _save_checkpoint(project_id, data, "REQUIREMENTS")
    append_log(project_id, "[requirements] Saved requirements.json")
    return project_summary(project_id, data, "REQUIREMENTS")


def validate_story_links(reqs: dict, stories_obj: dict) -> List[str]:
    fr_ids = {item.get("id") for item in reqs.get("functional_requirements", [])}
    nfr_ids = {item.get("id") for item in reqs.get("non_functional_requirements", [])}
    fr_ids.discard(None)
    nfr_ids.discard(None)
    invalid: List[str] = []
    for story in stories_obj.get("stories", []):
        sid = story.get("id", "UNKNOWN")
        links = story.get("links", {}) or {}
        for fid in links.get("fr", []) or []:
            if fid not in fr_ids:
                invalid.append(f"Story {sid} links unknown FR id: {fid}")
        for nid in links.get("nfr", []) or []:
            if nid not in nfr_ids:
                invalid.append(f"Story {sid} links unknown NFR id: {nid}")
    return invalid


def stories_minified(stories: list) -> list:
    return [
        {
            "id": story.get("id"),
            "role": story.get("role"),
            "story": story.get("story"),
            "links": story.get("links", {}),
        }
        for story in stories
    ]


def _listify(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    return [value]


def _resource_slug(value: str) -> str:
    slug = _snake_case(value).replace("_", "-")
    if slug.endswith("y") and not slug.endswith(("ay", "ey", "oy")):
        return f"{slug[:-1]}ies"
    if slug.endswith("s"):
        return slug
    return f"{slug}s"


def _architecture_roles_from_data(project_data: Dict[str, Any], arch: dict) -> List[str]:
    raw_roles = arch.get("roles") or arch.get("actors") or arch.get("user_roles") or []
    roles: List[str] = []
    for raw in _listify(raw_roles):
        role_text = str((raw.get("name") or raw.get("role") or raw.get("actor")) if isinstance(raw, dict) else raw)
        role, _, _desc = role_text.partition(":")
        clean = _clean_label(role)
        if clean and clean not in roles:
            roles.append(clean)
    cleaned_prompt = (project_data.get("cleaned_spec") or {}).get("cleaned_prompt") or {}
    for role_line in cleaned_prompt.get("Roles") or []:
        role, _, _desc = str(role_line).partition(":")
        clean = _clean_label(role)
        if clean and clean not in roles:
            roles.append(clean)
    for story in ((project_data.get("user_stories") or {}).get("stories") or []):
        if isinstance(story, dict):
            clean = _clean_label(str(story.get("role") or ""))
            if clean.lower() != "system" and clean and clean not in roles:
                roles.append(clean)
    for story in arch.get("stories_min") or []:
        if isinstance(story, dict):
            clean = _clean_label(str(story.get("role") or ""))
            if clean.lower() != "system" and clean and clean not in roles:
                roles.append(clean)
    for req in ((project_data.get("requirements") or {}).get("functional_requirements") or []):
        if isinstance(req, dict):
            clean = _clean_label(str(req.get("actor") or ""))
            if clean.lower() != "system" and clean and clean not in roles:
                roles.append(clean)
    for page in arch.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page_text = " ".join(str(page.get(key) or "") for key in ("name", "desc"))
        for role in ("Guest", "Staff", "Manager", "Agent", "Tenant", "Employee", "Member", "Doctor", "Patient", "Student", "Teacher", "Customer", "Client"):
            if re.search(rf"\b{role.lower()}\b", page_text.lower()) and role not in roles:
                roles.append(role)
    if "Admin" not in roles:
        roles.append("Admin")
    return roles or ["User", "Admin"]


def _architecture_entities_from_data(project_data: Dict[str, Any]) -> List[str]:
    cleaned_prompt = (project_data.get("cleaned_spec") or {}).get("cleaned_prompt") or {}
    raw_data = cleaned_prompt.get("Data") or {}
    if isinstance(raw_data, dict):
        entities = [_pascal_case(name) for name in raw_data.keys()]
    else:
        entities = []
    return [entity for entity in entities if entity]


def _coerce_pages(value: Any) -> List[dict]:
    pages: List[dict] = []
    for item in _listify(value):
        if isinstance(item, dict):
            pages.append(item)
        elif item:
            label = _clean_label(str(item))
            if label:
                pages.append({"name": label, "path": f"/{_resource_slug(label)}", "role_access": ["User"], "target_entity": None, "desc": label})
    return pages


def _coerce_endpoints(value: Any) -> List[dict]:
    endpoints: List[dict] = []
    for item in _listify(value):
        if isinstance(item, dict) and item.get("path"):
            endpoint = dict(item)
            endpoint["method"] = str(endpoint.get("method") or "GET").upper()
            endpoints.append(endpoint)
    return endpoints


def _fallback_pages(roles: List[str], entities: List[str]) -> List[dict]:
    non_admin = [role for role in roles if role.lower() != "admin"] or ["User"]
    pages: List[dict] = [
        {
            "name": f"{non_admin[0]} Dashboard",
            "path": "/",
            "role_access": [non_admin[0]],
            "target_entity": None,
            "desc": f"Main workspace for {non_admin[0]}",
        },
        {
            "name": "Admin Dashboard",
            "path": "/admin/dashboard",
            "role_access": ["Admin"],
            "target_entity": None,
            "desc": "Admin management overview",
        },
    ]
    for entity in entities:
        if entity == "User":
            continue
        resource = _resource_slug(entity)
        pages.append(
            {
                "name": f"Manage {entity}",
                "path": f"/admin/{resource}",
                "role_access": ["Admin"],
                "target_entity": entity,
                "desc": f"Admin management page for {entity}",
            }
        )
    return pages


def _fallback_endpoints(roles: List[str], entities: List[str]) -> List[dict]:
    read_roles = roles or ["User", "Admin"]
    endpoints: List[dict] = [
        {"method": "GET", "path": "/health", "role_access": [], "desc": "Public service health check"},
        {"method": "POST", "path": "/api/auth/register", "role_access": [], "desc": "Public registration"},
        {"method": "POST", "path": "/api/auth/login", "role_access": [], "desc": "JSON login"},
        {"method": "GET", "path": "/api/auth/me", "role_access": read_roles, "desc": "Current authenticated user"},
        {"method": "GET", "path": "/api/dashboard/stats", "role_access": read_roles, "desc": "Dashboard aggregate counts"},
    ]
    for entity in entities:
        if entity == "User":
            continue
        resource = _resource_slug(entity)
        endpoints.extend(
            [
                {"method": "GET", "path": f"/api/v1/{resource}", "role_access": read_roles, "desc": f"List {entity} records"},
                {"method": "POST", "path": f"/api/v1/{resource}", "role_access": ["Admin"], "desc": f"Create {entity} record"},
                {"method": "GET", "path": f"/api/v1/{resource}/{{id}}", "role_access": read_roles, "desc": f"Read {entity} record"},
                {"method": "PUT", "path": f"/api/v1/{resource}/{{id}}", "role_access": ["Admin"], "desc": f"Update {entity} record"},
                {"method": "DELETE", "path": f"/api/v1/{resource}/{{id}}", "role_access": ["Admin"], "desc": f"Delete {entity} record"},
            ]
        )
    return endpoints


def _entity_terms(entity: str) -> set[str]:
    base = _snake_case(entity)
    terms = {base, base.replace("_", " "), _resource_slug(entity).replace("-", " ")}
    parts = [part for part in base.split("_") if part]
    terms.update(parts)
    if base.endswith("_item"):
        terms.add(base[: -len("_item")].replace("_", " "))
    return {term for term in terms if term}


def _entity_actor_permissions(project_data: Dict[str, Any], entity: str, roles: List[str]) -> Dict[str, List[str]]:
    role_set = {role for role in roles if role != "Admin"} or {"User"}
    permissions = {"read": set(), "create": set(), "update": set(), "delete": {"Admin"}}
    terms = _entity_terms(entity)
    rows: List[tuple[str, str]] = []
    for story in ((project_data.get("user_stories") or {}).get("stories") or []):
        if isinstance(story, dict):
            rows.append((str(story.get("role") or ""), str(story.get("story") or "")))
    for req in ((project_data.get("requirements") or {}).get("functional_requirements") or []):
        if isinstance(req, dict):
            rows.append((str(req.get("actor") or ""), " ".join(str(req.get(key) or "") for key in ("shall", "description", "title"))))

    for actor, text in rows:
        actor = _clean_label(actor)
        if not actor or actor not in role_set:
            continue
        lower = text.lower()
        if not any(term in lower for term in terms):
            continue
        if any(token in lower for token in ("view", "browse", "see", "history", "schedule", "list", "manage")):
            permissions["read"].add(actor)
        if any(token in lower for token in ("book", "reserve", "place", "submit", "create", "request", "upload", "register", "add")):
            permissions["create"].add(actor)
        if any(token in lower for token in ("update", "cancel", "manage", "grade", "approve", "reject", "post", "edit", "status", "notes")):
            permissions["update"].add(actor)

    for key in ("read", "create", "update"):
        if not permissions[key]:
            permissions[key].update(role_set)
        permissions[key].add("Admin")
    return {key: sorted(value, key=lambda item: (item != "Admin", item)) for key, value in permissions.items()}


def _merge_missing_entity_endpoints(existing: List[dict], roles: List[str], entities: List[str], project_data: Dict[str, Any]) -> List[dict]:
    endpoints = list(existing)
    existing_paths = [str(endpoint.get("path") or "").lower() for endpoint in endpoints if isinstance(endpoint, dict)]
    for entity in entities:
        if entity == "User":
            continue
        resource = _resource_slug(entity)
        if any(f"/{resource}" in path for path in existing_paths):
            continue
        perms = _entity_actor_permissions(project_data, entity, roles)
        endpoints.extend(
            [
                {"method": "GET", "path": f"/api/v1/{resource}", "role_access": perms["read"], "desc": f"List {entity} records with role scoping"},
                {"method": "POST", "path": f"/api/v1/{resource}", "role_access": perms["create"], "desc": f"Create {entity} record"},
                {"method": "GET", "path": f"/api/v1/{resource}/{{id}}", "role_access": perms["read"], "desc": f"Read {entity} record"},
                {"method": "PUT", "path": f"/api/v1/{resource}/{{id}}", "role_access": perms["update"], "desc": f"Update {entity} record"},
                {"method": "DELETE", "path": f"/api/v1/{resource}/{{id}}", "role_access": ["Admin"], "desc": f"Delete {entity} record - Admin only"},
            ]
        )
    return endpoints


def normalize_architecture_shape(raw_arch: Any, project_data: Dict[str, Any]) -> Dict[str, Any]:
    arch = dict(raw_arch) if isinstance(raw_arch, dict) else {}
    if not arch:
        arch = {}
    if "stack" not in arch:
        stack = arch.get("tech_stack") or arch.get("technology_stack") or arch.get("technology") or {}
        arch["stack"] = stack if isinstance(stack, dict) else {}
    if not arch["stack"]:
        arch["stack"] = {
            "backend": "FastAPI",
            "db": "SQLite",
            "orm": "SQLAlchemy",
            "migrations": "Alembic",
            "frontend": "Plain HTML+CSS+JavaScript",
        }

    roles = _architecture_roles_from_data(project_data, arch)
    entities = _architecture_entities_from_data(project_data)
    arch["roles"] = roles

    modules = arch.get("modules") or arch.get("module") or arch.get("components") or arch.get("features") or arch.get("services")
    if isinstance(modules, dict):
        modules = list(modules.keys())
    arch["modules"] = [_clean_label(str(item)) for item in _listify(modules) if _clean_label(str(item))]
    if not arch.get("modules"):
        arch["modules"] = ["auth", "dashboard", "crud", *[_snake_case(entity) for entity in entities if entity != "User"]]

    pages = _coerce_pages(arch.get("pages") or arch.get("screens") or arch.get("ui_pages") or arch.get("views"))
    arch["pages"] = pages or _fallback_pages(roles, entities)

    endpoints = _coerce_endpoints(
        arch.get("endpoints")
        or arch.get("api_endpoints")
        or arch.get("apis")
        or arch.get("api")
        or arch.get("routes")
        or arch.get("backend_routes")
    )
    arch["endpoints"] = _merge_missing_entity_endpoints(endpoints or _fallback_endpoints(roles, entities), roles, entities, project_data)
    return arch


def _coerce_field(value: Any) -> dict | None:
    if isinstance(value, dict):
        name = value.get("name") or value.get("field") or value.get("column")
        if not name:
            return None
        field = dict(value)
        field["name"] = _snake_case(str(name))
        field["type"] = str(field.get("type") or field.get("datatype") or field.get("data_type") or _field_type(field["name"]))
        if field["name"] == "id":
            field["pk"] = True
            field["nullable"] = False
        return field
    name = _snake_case(str(value or ""))
    if not name:
        return None
    return {"name": name, "type": _field_type(name)}


def _coerce_entity(value: Any, name_hint: str | None = None) -> dict | None:
    if isinstance(value, dict):
        raw_name = value.get("name") or value.get("entity") or value.get("table") or name_hint
        if not raw_name:
            return None
        raw_fields = value.get("fields") or value.get("columns") or value.get("attributes") or []
    else:
        raw_name = name_hint or str(value or "")
        raw_fields = []
    name = _pascal_case(str(raw_name))
    if not name:
        return None
    if isinstance(raw_fields, dict):
        raw_fields = [{"name": key, **(val if isinstance(val, dict) else {"type": val})} for key, val in raw_fields.items()]
    fields = [field for field in (_coerce_field(item) for item in _listify(raw_fields)) if field]
    existing = {field["name"] for field in fields}
    if "id" not in existing:
        fields.insert(0, {"name": "id", "type": "uuid", "pk": True, "nullable": False})
    if name == "User":
        required = [
            ("email", "string"),
            ("password_hash", "string"),
            ("role", "string"),
            ("full_name", "string"),
        ]
        for field_name, field_type in required:
            if field_name not in {field["name"] for field in fields}:
                fields.append({"name": field_name, "type": field_type})
    for audit_name in ("created_at", "updated_at"):
        if audit_name not in {field["name"] for field in fields}:
            fields.append({"name": audit_name, "type": "datetime"})
    return {"name": name, "fields": fields}


def normalize_data_model_shape(raw_dm: Any) -> Dict[str, Any]:
    dm = dict(raw_dm) if isinstance(raw_dm, dict) else {}
    raw_entities = dm.get("entities") or dm.get("tables") or dm.get("models") or dm.get("schema") or []
    entities: List[dict] = []
    if isinstance(raw_entities, dict):
        raw_entities = [{"name": key, **(val if isinstance(val, dict) else {"fields": val})} for key, val in raw_entities.items()]
    for item in _listify(raw_entities):
        entity = _coerce_entity(item)
        if entity:
            entities.append(entity)
    if entities and not any(entity.get("name") == "User" for entity in entities):
        entities.insert(0, _coerce_entity({"name": "User", "fields": []}) or {"name": "User", "fields": []})

    raw_relationships = dm.get("relationships") or dm.get("relations") or dm.get("foreign_keys") or []
    relationships: List[dict] = []
    for item in _listify(raw_relationships):
        if not isinstance(item, dict):
            continue
        rel_from = _pascal_case(str(item.get("from") or item.get("source") or item.get("child") or ""))
        rel_to = _pascal_case(str(item.get("to") or item.get("target") or item.get("parent") or ""))
        fk_field = _snake_case(str(item.get("fk_field") or item.get("foreign_key") or item.get("field") or ""))
        if rel_from and rel_to and fk_field:
            relationships.append(
                {
                    "from": rel_from,
                    "to": rel_to,
                    "type": item.get("type") or item.get("relation") or "many-to-one",
                    "fk_field": fk_field,
                }
            )
    return {"entities": entities, "relationships": relationships}


def _story_actor(req: dict) -> str:
    actor = _clean_label(str(req.get("actor") or ""))
    if actor:
        return actor
    text = str(req.get("shall") or req.get("description") or "")
    match = re.search(r"\bfor\s+([A-Z][A-Za-z ]{1,40})\s+to\b", text)
    if match:
        return _clean_label(match.group(1))
    return "User"


def _story_goal(req: dict) -> str:
    text = _clean_label(str(req.get("shall") or req.get("description") or req.get("title") or "use this capability"))
    text = re.sub(r"^The system shall\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+for\s+[A-Z][A-Za-z ]{1,40}\s+to\s+.*$", "", text)
    replacements = [
        (r"^allow\s+[^ ]+\s+to\s+", ""),
        (r"^enable\s+[^ ]+\s+to\s+", ""),
        (r"^permit\s+[^ ]+\s+to\s+", ""),
        (r"^provide\s+[^ ]+\s+with\s+", "use "),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return _clean_label(text[:180]) or "use this capability"


def _story_benefit(req: dict, actor: str, goal: str) -> str:
    text = str(req.get("shall") or "")
    match = re.search(r"\bfor\s+[A-Z][A-Za-z ]{1,40}\s+to\s+(.+)$", text)
    if match:
        return _clean_label(match.group(1).rstrip("."))
    lower_goal = goal.lower()
    if "manage" in lower_goal:
        return "keep the workspace accurate and up to date"
    if "view" in lower_goal or "browse" in lower_goal:
        return "find the information I need quickly"
    if "submit" in lower_goal or "create" in lower_goal or "book" in lower_goal:
        return "complete my workflow without administrator help"
    if actor.lower() == "admin":
        return "control the application safely"
    return "finish my task in the application"


def generate_user_stories(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    reqs = data.get("requirements")
    if not reqs:
        raise ValueError("Generate requirements first.")
    functional_count = len(reqs.get("functional_requirements") or [])
    non_functional_count = len(reqs.get("non_functional_requirements") or [])
    settings = load_settings()
    append_log(
        project_id,
        (
            f"[stories] Asking Ollama model {settings['model_architect']} to write stories "
            f"for {functional_count} functional and {non_functional_count} non-functional requirements"
        ),
    )
    result = safe_llm_json(
        "USER_STORIES",
        USER_STORIES_SYSTEM,
        {
            "cleaned_spec": data.get("cleaned_spec", {}),
            "requirements": reqs,
        },
        temperature=0.2,
        num_predict=8192,
        model=settings["model_architect"],
        num_ctx=settings["model_ctx_architect"],
        require_keys_list=["stories"],
        timeout_sec=settings["timeout_requirements_sec"],
        retries=1,
        json_repair_timeout_sec=settings["timeout_json_repair_sec"],
        json_repair_retries=2,
        json_repair_num_predict=8192,
        json_validation_retries=1,
    )
    if not result.get("stories"):
        append_log(project_id, "[stories:error] Ollama returned no stories")
        raise ValueError("USER_STORIES: Ollama returned no stories")
    invalid_links = validate_story_links(reqs, result)
    for item in invalid_links[:10]:
        append_log(project_id, f"[stories:warn] {item}")
    data["user_stories"] = {"stories": result["stories"]}
    _clear_downstream_stage_data(data, "USER_STORIES")
    _save_checkpoint(project_id, data, "USER_STORIES")
    append_log(project_id, f"[stories] Generated {len(result['stories'])} stories")
    return project_summary(project_id, data, "USER_STORIES")


def generate_architecture(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    reqs = data.get("requirements")
    stories = data.get("user_stories")
    if not reqs or not stories:
        raise ValueError("Generate requirements and user stories first.")
    settings = load_settings()
    payload = {"requirements": reqs, "stories_min": stories_minified(stories.get("stories", []))}
    append_log(project_id, f"[architecture] Asking Ollama model {settings['model_architect']} to design stack, pages, modules, and API")
    raw_arch = safe_llm_json(
        "ARCHITECTURE",
        ARCHITECTURE_SYSTEM,
        payload,
        temperature=0.2,
        num_predict=8192,
        model=settings["model_architect"],
        num_ctx=settings["model_ctx_architect"],
        require_keys_list=["stack", "roles", "modules", "pages", "endpoints"],
        timeout_sec=settings["timeout_architecture_sec"],
        retries=1,
        json_repair_timeout_sec=settings["timeout_json_repair_sec"],
        json_repair_retries=2,
        json_repair_num_predict=8192,
        json_validation_retries=1,
    )
    arch = normalize_architecture_shape(raw_arch, data)
    if not arch.get("stack"):
        raise ValueError("ARCHITECTURE: Ollama returned no stack")
    if not arch.get("roles"):
        raise ValueError("ARCHITECTURE: Ollama returned no roles")
    if not arch.get("modules"):
        raise ValueError("ARCHITECTURE: Ollama returned no modules")
    if not isinstance(arch.get("pages"), list) or not arch.get("pages"):
        raise ValueError("ARCHITECTURE: Ollama returned no pages")
    if not isinstance(arch.get("endpoints"), list) or not arch.get("endpoints"):
        raise ValueError("ARCHITECTURE: Ollama returned no endpoints")
    try:
        from builder.architecture_guard import normalize_architecture

        normalized, fixes = normalize_architecture({"architecture": arch})
        arch = normalized["architecture"]
        for fix in fixes:
            append_log(project_id, f"[architecture] {fix}")
    except Exception as exc:
        append_log(project_id, f"[architecture:warn] Normalization skipped: {exc}")
    data["architecture"] = arch
    _clear_downstream_stage_data(data, "ARCHITECTURE")
    _save_checkpoint(project_id, data, "ARCHITECTURE")
    append_log(project_id, "[architecture] Complete")
    return project_summary(project_id, data, "ARCHITECTURE")


def generate_data_model(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    reqs = data.get("requirements")
    arch = data.get("architecture")
    if not reqs or not arch:
        raise ValueError("Generate requirements and architecture first.")
    settings = load_settings()
    payload = {
        "cleaned_spec": data.get("cleaned_spec", {}),
        "requirements": reqs,
        "user_stories": data.get("user_stories", {}),
        "architecture": arch,
    }
    append_log(project_id, f"[data-model] Asking Ollama model {settings['model_architect']} to design the database schema")
    raw_dm = safe_llm_json(
        "DATA_MODEL",
        DATA_MODEL_SYSTEM,
        payload,
        temperature=0.2,
        num_predict=8192,
        model=settings["model_architect"],
        num_ctx=settings["model_ctx_architect"],
        require_keys_list=["entities", "relationships"],
        timeout_sec=settings["timeout_data_model_sec"],
        retries=1,
        json_repair_timeout_sec=settings["timeout_json_repair_sec"],
        json_repair_retries=2,
        json_repair_num_predict=8192,
        json_validation_retries=1,
    )
    dm = normalize_data_model_shape(raw_dm)
    if not dm.get("entities"):
        append_log(project_id, "[data-model:error] Ollama returned no entities")
        raise ValueError("DATA_MODEL: Ollama returned no entities. Retry or make the Entities section more explicit.")
    data["data_model"] = dm
    try:
        from builder.data_model_guard import normalize_data_model

        data, fixes = normalize_data_model(data)
        for fix in fixes:
            append_log(project_id, f"[data-model] {fix}")
    except Exception as exc:
        append_log(project_id, f"[data-model:warn] Normalization skipped: {exc}")
    _clear_downstream_stage_data(data, "DATA_MODEL")
    _save_checkpoint(project_id, data, "DATA_MODEL")
    append_log(project_id, "[data-model] Complete")
    return project_summary(project_id, data, "DATA_MODEL")


def generate_srs(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    needed = ["cleaned_spec", "requirements", "user_stories", "architecture", "data_model"]
    missing = [key for key in needed if key not in data]
    if missing:
        raise ValueError(f"Missing stages before SRS generation: {missing}")
    settings = load_settings()
    payload = {key: data[key] for key in needed}
    append_log(project_id, f"[srs] Asking Ollama model {settings['model_architect']} to write SRS markdown")
    markdown = ask_llm(
        system=SRS_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        num_predict=6000,
        model=settings["model_architect"],
        num_ctx=settings["model_ctx_architect"],
        timeout_sec=settings["timeout_srs_sec"],
        retries=1,
    )
    data["srs_document"] = markdown
    _clear_downstream_stage_data(data, "SRS_DOCUMENTATION")
    project_dir = CHECKPOINTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "srs.md").write_text(markdown, encoding="utf-8")
    _save_checkpoint(project_id, data, "SRS_DOCUMENTATION")
    append_log(project_id, "[srs] Saved srs.md")
    return project_summary(project_id, data, "SRS_DOCUMENTATION")


def regenerate_stage_and_recascade(
    project_id: str,
    stage_to_regenerate: str,
    reason: str,
) -> Dict[str, Any]:
    """
    Regenerate one structural upstream stage and replay dependent stages.

    This keeps the default pipeline waterfall-shaped, but gives code
    generation a user-approved backward recovery path when diagnosis points to
    bad architecture or data-model context.
    """
    _validate_project_id(project_id)
    stage_to_regenerate = str(stage_to_regenerate or "").strip().upper()
    if stage_to_regenerate not in {"ARCHITECTURE", "DATA_MODEL"}:
        raise ValueError(f"Regeneration not supported for stage: {stage_to_regenerate}")

    data, _ = load_checkpoint(project_id)
    preserved_ui_selection = data.get("ui_selection")
    append_log(project_id, f"[recovery] Regenerating {stage_to_regenerate}. Reason: {reason}")
    save_checkpoint_history(project_id, data, f"PRE_RECOVERY_{stage_to_regenerate}")

    cascade_order = ["ARCHITECTURE", "DATA_MODEL", "SRS_DOCUMENTATION"]
    start_index = cascade_order.index(stage_to_regenerate)
    stages_to_rerun = cascade_order[start_index:]
    stage_fn_map = {
        "ARCHITECTURE": generate_architecture,
        "DATA_MODEL": generate_data_model,
        "SRS_DOCUMENTATION": generate_srs,
    }

    results: List[Dict[str, Any]] = []
    for stage in stages_to_rerun:
        append_log(project_id, f"[recovery] Re-cascading: {stage}")
        result = stage_fn_map[stage](project_id)
        results.append({"stage": stage, "result": result})

    data, latest_stage = load_checkpoint(project_id)
    if preserved_ui_selection and not data.get("ui_selection"):
        data["ui_selection"] = preserved_ui_selection
        if "architecture" in data:
            arch = data["architecture"]
            arch["theme"] = preserved_ui_selection.get("theme_vars", {})
            arch["bootstrap_css"] = preserved_ui_selection.get("bootstrap_css")
            arch["layout"] = preserved_ui_selection.get("layout_key")
            arch["ui_key"] = preserved_ui_selection.get("ui_key")
            arch["layout_requirements"] = preserved_ui_selection.get("layout_requirements", [])
        latest_stage = "UI_SELECTION"
        append_log(project_id, "[recovery] Preserved existing UI selection after structural re-cascade")
    data.pop("recovery_diagnosis", None)
    data["last_recovery"] = {
        "regenerated_from": stage_to_regenerate,
        "stages_rerun": stages_to_rerun,
        "reason": reason,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _save_checkpoint(project_id, data, latest_stage)
    append_log(project_id, f"[recovery] Re-cascade complete. {len(stages_to_rerun)} stage(s) regenerated.")
    return {
        "regenerated_from": stage_to_regenerate,
        "stages_rerun": stages_to_rerun,
        "results": results,
        "reason": reason,
    }


def _diagnose_and_store_recovery(
    project_id: str,
    data: dict,
    output: str,
    cycles: int,
    stage: str,
) -> Dict[str, Any] | None:
    try:
        from builder.failure_classifier import classify_failure

        diagnosis = classify_failure(data, output, cycles)
        if diagnosis and diagnosis.get("category") != "CODE_BUG":
            data["recovery_diagnosis"] = diagnosis
            _save_checkpoint(project_id, data, stage)
            append_log(
                project_id,
                f"[recovery] Suggested {diagnosis.get('suggested_stage_to_regenerate')}: {diagnosis.get('reason')}",
            )
        return diagnosis
    except Exception as exc:
        append_log(project_id, f"[recovery:warn] Failure diagnosis skipped: {exc}")
        return None


def _restore_ui_selection(data: dict, preserved_ui_selection: dict | None) -> None:
    if not preserved_ui_selection:
        return
    data["ui_selection"] = preserved_ui_selection
    if "architecture" in data:
        arch = data["architecture"]
        arch["theme"] = preserved_ui_selection.get("theme_vars", {})
        arch["bootstrap_css"] = preserved_ui_selection.get("bootstrap_css")
        arch["layout"] = preserved_ui_selection.get("layout_key")
        arch["ui_key"] = preserved_ui_selection.get("ui_key")
        arch["layout_requirements"] = preserved_ui_selection.get("layout_requirements", [])


def _apply_deterministic_data_model_recovery(
    project_id: str,
    diagnosis: Dict[str, Any],
    reason: str,
) -> bool:
    if not diagnosis.get("deterministic_fixes"):
        return False
    try:
        from builder.app_contract import build_app_contract
        from builder.data_model_guard import recover_data_model_from_failure

        data, _ = load_checkpoint(project_id)
        preserved_ui_selection = data.get("ui_selection")
        save_checkpoint_history(project_id, data, "PRE_RECOVERY_DATA_MODEL_DETERMINISTIC")
        recovered, fixes = recover_data_model_from_failure(data, diagnosis)
        if not fixes:
            append_log(project_id, "[recovery:auto] No deterministic DATA_MODEL fixes applied; falling back to stage regeneration.")
            return False
        data = recovered
        _clear_downstream_stage_data(data, "DATA_MODEL")
        _restore_ui_selection(data, preserved_ui_selection)
        data["last_recovery"] = {
            "regenerated_from": "DATA_MODEL",
            "mode": "deterministic_guard",
            "reason": reason,
            "fixes": fixes,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        build_app_contract(data)
        _save_checkpoint(project_id, data, "DATA_MODEL")
        for fix in fixes:
            append_log(project_id, f"[recovery:data-model] {fix}")
        append_log(project_id, "[recovery:data-model] Rebuilt AppContract after deterministic DATA_MODEL recovery")

        append_log(project_id, "[recovery] Re-cascading: SRS_DOCUMENTATION")
        generate_srs(project_id)
        data, latest_stage = load_checkpoint(project_id)
        if preserved_ui_selection and not data.get("ui_selection"):
            _restore_ui_selection(data, preserved_ui_selection)
            latest_stage = "UI_SELECTION"
            append_log(project_id, "[recovery] Preserved existing UI selection after deterministic DATA_MODEL recovery")
        _save_checkpoint(project_id, data, latest_stage)
        return True
    except Exception as exc:
        append_log(project_id, f"[recovery:data-model:warn] Deterministic DATA_MODEL recovery failed: {exc}")
        return False


def _auto_recover_code_generation(
    project_id: str,
    options: Dict[str, Any],
    diagnosis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not diagnosis or diagnosis.get("category") == "CODE_BUG":
        return None

    suggested_stage = str(diagnosis.get("suggested_stage_to_regenerate") or "").strip().upper()
    if suggested_stage not in AUTO_RECOVERY_STAGES:
        return None

    recovery_chain = [str(stage).upper() for stage in (options.get("_auto_recovery_chain") or [])]
    if suggested_stage in recovery_chain:
        append_log(
            project_id,
            f"[recovery:auto] {suggested_stage} was already regenerated in this recovery chain; surfacing failure.",
        )
        return None

    try:
        attempt = int(options.get("_auto_recovery_attempt", 0) or 0)
    except (TypeError, ValueError):
        attempt = 0
    if attempt >= MAX_AUTO_RECOVERY_ATTEMPTS:
        append_log(
            project_id,
            f"[recovery:auto] Recovery limit reached for {suggested_stage}; surfacing failure.",
        )
        return None

    reason = str(diagnosis.get("reason") or "Generated app failed validation.")
    append_log(
        project_id,
        (
            f"[recovery:auto] Attempt {attempt + 1}/{MAX_AUTO_RECOVERY_ATTEMPTS}: "
            f"regenerating {suggested_stage} and re-running code generation."
        ),
    )
    deterministic_applied = False
    if suggested_stage == "DATA_MODEL":
        deterministic_applied = _apply_deterministic_data_model_recovery(project_id, diagnosis, reason)
    if not deterministic_applied:
        regenerate_stage_and_recascade(project_id, suggested_stage, reason)
    retry_options = dict(options)
    retry_options["_auto_recovery_attempt"] = attempt + 1
    retry_options["_auto_recovery_chain"] = [
        *recovery_chain,
        suggested_stage,
    ]
    return generate_code(project_id, retry_options)


def save_ui_selection(project_id: str, ui_selection: Dict[str, Any]) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    data["ui_selection"] = ui_selection
    if "architecture" in data:
        arch = data["architecture"]
        arch["theme"] = ui_selection.get("theme_vars", {})
        arch["bootstrap_css"] = ui_selection.get("bootstrap_css")
        arch["layout"] = ui_selection.get("layout_key")
        arch["ui_key"] = ui_selection.get("ui_key")
        arch["layout_requirements"] = ui_selection.get("layout_requirements", [])
    _clear_downstream_stage_data(data, "UI_SELECTION")
    _save_checkpoint(project_id, data, "UI_SELECTION")
    append_log(project_id, "[ui] Selection saved")
    return project_summary(project_id, data, "UI_SELECTION")


def collect_generated_project_snapshot(repo_path: str) -> dict:
    if not repo_path:
        return {"available": False, "reason": "No repo_path recorded."}
    repo = Path(repo_path)
    if not repo.exists():
        return {"available": False, "reason": f"Generated repository not found: {repo_path}"}
    interesting_suffixes = {".py", ".html", ".j2", ".txt", ".ini", ".yml", ".yaml", ".json", ".md"}
    ignored_dirs = {".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    files = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in interesting_suffixes:
            continue
        if any(part in ignored_dirs for part in path.relative_to(repo).parts):
            continue
        rel = str(path.relative_to(repo)).replace("\\", "/")
        files.append({"path": rel, "size_bytes": path.stat().st_size if path.exists() else None})
    return {"available": True, "repo_path": str(repo), "file_count": len(files), "files": files[:80]}


def validate_generated_code(out_dir: str) -> List[str]:
    issues: List[str] = []
    repo = Path(out_dir)
    critical_files = [
        "app/__init__.py",
        "app/main.py",
        "app/models.py",
        "app/schemas.py",
        "app/db.py",
        "app/auth.py",
        "app/deps.py",
        "app/routers/__init__.py",
        "app/routers/auth.py",
        "app/routers/generic_crud.py",
        "requirements.txt",
        "seed.py",
        ".env.example",
        "frontend_templates/index.html",
        "frontend_templates/app.html",
        "frontend_templates/login.html",
        "frontend_templates/register.html",
        "frontend_templates/entity_list.html",
        "frontend_templates/entity_form.html",
    ]
    for rel in critical_files:
        if not (repo / rel).exists():
            issues.append(f"Missing critical file: {rel}")
    for py_file in repo.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue
        try:
            compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec")
        except SyntaxError as exc:
            issues.append(f"Syntax error in {py_file.relative_to(repo)}: {exc}")
    jinja_files = list(repo.rglob("*.j2"))
    for path in jinja_files:
        issues.append(f"Jinja template is forbidden: {path.relative_to(repo)}")
    for html_file in repo.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        if any(marker in content for marker in ("{{", "{%", "{#")):
            issues.append(f"Template syntax in plain HTML: {html_file.relative_to(repo)}")
        has_api_helper = "apiFetch" in content or "function api(" in content or "fetch(" in content
        if "access_token" not in content or not has_api_helper:
            issues.append(f"Canonical auth helpers missing: {html_file.relative_to(repo)}")
    required_contracts = {
        "app/main.py": ("/health", "/api/dashboard/stats", "app.html"),
        "app/routers/auth.py": ("/register", "/login", "/login/form", "PUBLIC_REGISTER_ROLE"),
        "app/routers/generic_crud.py": ("get_current_user", "model_dump"),
        "seed.py": ("Base.metadata.create_all", "Admin"),
    }
    for rel, markers in required_contracts.items():
        path = repo / rel
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in content:
                issues.append(f"Missing {marker!r} contract in {rel}")
        if rel == "seed.py" and "drop_all" in content:
            issues.append("seed.py may not call drop_all")
    return issues


def validate_before_serve(out_dir: str) -> List[str]:
    """Strict static gate used after generation, healing, and before startup."""
    return validate_generated_code(out_dir)


def _run_engine_contract_preflight(project_id: str, out_dir: str, data: dict, stage: str) -> dict:
    from builder.contract_validator import EngineContractError, assert_engine_contract_preflight

    append_log(project_id, "[contract] Running static AppContract pre-flight")
    try:
        report = assert_engine_contract_preflight(out_dir, data)
    except EngineContractError as exc:
        report = exc.to_dict()
        message = str(exc)
        data["tdd_passed"] = False
        data["tdd_skipped"] = True
        data["tdd_error"] = message[-3000:]
        data["engine_contract_error"] = report
        data["validation_issues"] = [message]
        data["recovery_diagnosis"] = {
            "category": "engine_contract",
            "suggested_stage_to_regenerate": "CODE_GENERATION",
            "confidence": 1.0,
            "reason": "Generated source disagrees with builder/app_contract.py. This is an engine bug; self-healing was skipped.",
            "details": report,
        }
        for line in message.splitlines():
            append_log(project_id, f"[contract:error] {line}")
        _save_checkpoint(project_id, data, stage)
        raise
    data["engine_contract_preflight"] = {
        "ok": True,
        "expected_routes_count": len(report.get("expected_routes") or []),
        "exposed_routes_count": len(report.get("exposed_routes") or []),
    }
    data.pop("engine_contract_error", None)
    append_log(
        project_id,
        (
            "[contract] Pre-flight passed "
            f"({len(report.get('expected_routes') or [])} expected routes, "
            f"{len(report.get('exposed_routes') or [])} exposed routes)"
        ),
    )
    return report


def _make_ask_llm_for_project(project_id: str) -> Callable:
    def _fn(system: str, user: str, num_predict: int = 4096, **kwargs: Any) -> str:
        settings = load_settings()
        append_log(project_id, f"[llm] Requesting code/refactor output from {settings['model_coder']}")
        if settings.get("single_model_mode", True):
            num_predict = min(num_predict, settings["model_predict_code_cap"])
        kwargs.setdefault("timeout_sec", settings["timeout_code_generation_sec"])
        kwargs.setdefault("retries", 0)
        return ask_llm(system, user, num_predict=num_predict, **kwargs)

    return _fn


def generate_code(project_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
    _validate_project_id(project_id)
    options = {
        **(options or {}),
        "build_from_scratch": True,
        "run_tdd": True,
        "run_refactor": False,
        "debug_logging": False,
    }
    try:
        auto_recovery_attempt = int(options.get("_auto_recovery_attempt", 0) or 0)
    except (TypeError, ValueError):
        auto_recovery_attempt = 0
    data, current_stage = load_checkpoint(project_id)
    needed = ["cleaned_spec", "requirements", "user_stories", "architecture", "data_model"]
    missing = [key for key in needed if key not in data]
    if missing:
        raise ValueError(f"Missing stages before code generation: {missing}")

    stop_server(project_id)
    if auto_recovery_attempt <= 0:
        PROJECT_LOGS[project_id] = []
    else:
        append_log(
            project_id,
            (
                f"[recovery:auto] Retrying code generation after upstream recovery "
                f"({auto_recovery_attempt}/{MAX_AUTO_RECOVERY_ATTEMPTS})"
            ),
        )
    try:
        from builder.architecture_guard import normalize_architecture

        data, fixes = normalize_architecture(data)
        for fix in fixes:
            append_log(project_id, f"[architecture] {fix}")
        if fixes:
            _save_checkpoint(project_id, data, current_stage)
    except Exception as exc:
        append_log(project_id, f"[architecture:warn] Normalization skipped: {exc}")
    data["project_id"] = project_id
    data["generation_options"] = options
    data["codegen_context"] = {
        "project_id": project_id,
        "cleaned_spec": data.get("cleaned_spec", {}),
        "requirements": data.get("requirements", {}),
        "user_stories": data.get("user_stories", {}),
        "architecture": data.get("architecture", {}),
        "data_model": data.get("data_model", {}),
        "ui_selection": data.get("ui_selection", {}),
        "source_policy": "llm_from_scratch_plain_source",
    }
    append_log(project_id, "[blueprint] Generating custom project blueprint")

    blueprint = generate_project_blueprint(data)
    data["blueprint"] = blueprint
    checkpoint_dir = CHECKPOINTS_DIR / project_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / "blueprint.json").write_text(json.dumps(blueprint, indent=2, ensure_ascii=False), encoding="utf-8")

    append_log(project_id, "[manifest] Creating file manifest")
    manifest = generate_file_manifest(data, blueprint)
    data["file_manifest"] = manifest
    (checkpoint_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    progress = lambda message: append_log(project_id, message)
    ask_fn = _make_ask_llm_for_project(project_id)
    if not options.get("build_from_scratch", True):
        append_log(project_id, "[codegen] Template mode is disabled; using from-scratch generation")
    append_log(project_id, "[codegen] Starting repository generation")
    out_dir = generate_repo(project_id, data, ask_llm_fn=ask_fn, progress_callback=progress)

    artifacts_dir = Path(out_dir) / "_builder_artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    (artifacts_dir / "blueprint.json").write_text(json.dumps(blueprint, indent=2, ensure_ascii=False), encoding="utf-8")
    (artifacts_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (artifacts_dir / "project_data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    issues = validate_before_serve(out_dir)
    data["repo_path"] = out_dir
    data["build_done"] = False
    data["validation_issues"] = issues
    for issue in issues:
        append_log(project_id, f"[validate:warn] {issue}")
    if issues:
        diagnosis = _diagnose_and_store_recovery(project_id, data, "\n".join(issues), 0, current_stage)
        recovered = _auto_recover_code_generation(project_id, options, diagnosis)
        if recovered is not None:
            return recovered
        raise RuntimeError("Generated source failed validation: " + "; ".join(issues[:10]))

    latest_dir = Path(out_dir).parent.parent / "latest"
    if latest_dir.exists():
        if latest_dir.is_symlink():
            latest_dir.unlink()
        else:
            shutil.rmtree(latest_dir)
    shutil.copytree(out_dir, latest_dir, dirs_exist_ok=True)
    append_log(project_id, "[latest] Copied repository to generated_apps/projects/latest")
    _save_checkpoint(project_id, data, "CODE_GENERATION")
    append_log(project_id, "[codegen] Core source complete and checkpoint saved")

    append_log(project_id, "[tdd] Running automatic validation and self-healing")
    run_tdd_pass(project_id, out_dir, data)
    if not data.get("tdd_passed"):
        diagnosis = data.get("recovery_diagnosis")
        if not diagnosis:
            diagnosis = _diagnose_and_store_recovery(
                project_id,
                data,
                data.get("tdd_error", "Runtime validation failed"),
                2,
                "CODE_GENERATION",
            )
        recovered = _auto_recover_code_generation(project_id, options, diagnosis)
        if recovered is not None:
            return recovered
        _save_checkpoint(project_id, data, "CODE_GENERATION")
        raise RuntimeError("Generated app did not pass automatic runtime tests and self-healing.")

    final_generation_issues = validate_before_serve(out_dir)
    if final_generation_issues:
        diagnosis = _diagnose_and_store_recovery(
            project_id,
            data,
            "\n".join(final_generation_issues),
            0,
            "CODE_GENERATION",
        )
        recovered = _auto_recover_code_generation(project_id, options, diagnosis)
        if recovered is not None:
            return recovered
        raise RuntimeError(
            "Generated source failed post-processing validation: "
            + "; ".join(final_generation_issues[:10])
        )
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(out_dir, latest_dir, dirs_exist_ok=True)
    append_log(project_id, "[latest] Refreshed with final validated source")

    _save_checkpoint(project_id, data, "CODE_GENERATION")
    append_log(project_id, "[codegen] Complete")
    return project_summary(project_id, data, "CODE_GENERATION")


def run_refactor_pass(project_id: str, out_dir: str) -> None:
    repo = Path(out_dir)
    target = repo / "frontend_templates" / "app.html"
    if not target.exists():
        append_log(project_id, "[refactor] No dashboard source found; skipping")
        return
    original = target.read_text(encoding="utf-8")
    prompt = (
        "You are a senior frontend architect. Refactor this standalone plain HTML dashboard "
        "to be polished, domain-specific, and robust. Preserve API paths and JavaScript ids. "
        "Do not use Jinja or template syntax. Output only raw HTML."
    )
    settings = load_settings()
    improved = ask_llm(
        prompt,
        original,
        model=settings["model_coder"],
        num_predict=4000,
        timeout_sec=settings["timeout_refactor_sec"],
        retries=1,
    )
    cleaned = re.sub(r"^```[\w]*\s*", "", improved.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    if len(cleaned) > 50 and not any(marker in cleaned for marker in ("{{", "{%", "{#")):
        target.write_text(cleaned, encoding="utf-8")
        append_log(project_id, "[refactor] Updated dashboard source")


def run_tdd_pass(project_id: str, out_dir: str, data: dict) -> None:
    data.pop("tdd_skipped", None)
    _run_engine_contract_preflight(project_id, out_dir, data, "CODE_GENERATION")
    append_log(project_id, "[tdd] Installing runtime test dependencies and starting focused healing")
    from builder.runtime_self_healing import run_focused_runtime_healing

    venv_dir = Path(out_dir) / ".venv"
    py_exe = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    python_exe = str(py_exe if py_exe.exists() else Path(sys.executable))
    env = _subprocess_env(cwd=Path(out_dir))
    subprocess.run(
        [python_exe, "-m", "pip", "install", "-q", "pytest", "pytest-asyncio", "httpx", "requests", "uvicorn"],
        cwd=out_dir,
        capture_output=True,
        env=env,
        timeout=300,
    )

    last_error = ""
    for pass_number in range(1, 3):
        try:
            append_log(project_id, f"[tdd] Validation pass {pass_number}/2")
            result = run_focused_runtime_healing(
                project_dir=out_dir,
                ask_llm_fn=_make_ask_llm_for_project(project_id),
                project_data=data,
                progress_callback=lambda message: append_log(project_id, message),
                venv_python=python_exe,
                env=env,
            )
            data["tdd_passed"] = bool(result.get("success"))
            data["tdd_history"] = result.get("summary", {})
            if result.get("diagnosis"):
                data["recovery_diagnosis"] = result["diagnosis"]
            if data["tdd_passed"]:
                data.pop("tdd_error", None)
                data.pop("recovery_diagnosis", None)
                break
            last_error = result.get("last_test_output", "Runtime validation failed")
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            append_log(project_id, f"[tdd:warn] Pass {pass_number} failed: {last_error}")
    else:
        data["tdd_passed"] = False

    if not data.get("tdd_passed"):
        data["tdd_error"] = last_error[-3000:]
        if not data.get("recovery_diagnosis"):
            _diagnose_and_store_recovery(project_id, data, last_error, 2, "CODE_GENERATION")
    append_log(project_id, f"[tdd] Complete success={bool(data.get('tdd_passed'))}")


def build_generated_app(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    repo_path = data.get("repo_path")
    if not repo_path:
        raise ValueError("No generated repository path found.")
    if not data.get("tdd_passed"):
        raise ValueError("Code generation has not passed automatic runtime tests and self-healing yet.")
    repo = Path(repo_path)
    if not repo.exists():
        raise ValueError(f"Generated repository not found: {repo}")
    PROJECT_LOGS[project_id] = []
    append_log(project_id, f"[build] Building {repo}")
    stop_server(project_id)
    time.sleep(1)
    preflight_issues = validate_before_serve(str(repo))
    if preflight_issues:
        _diagnose_and_store_recovery(project_id, data, "\n".join(preflight_issues), 0, "BUILD_AND_RUN")
        raise RuntimeError(
            "Pre-build source validation failed: " + "; ".join(preflight_issues[:10])
        )

    for db_file in repo.glob("*.db"):
        try:
            db_file.unlink(missing_ok=True)
            append_log(project_id, f"[build] Removed stale database {db_file.name}")
        except Exception as exc:
            append_log(project_id, f"[build:warn] Could not remove {db_file.name}: {exc}")

    venv_dir = repo / ".venv"
    python_exe = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    build_env = _subprocess_env(cwd=repo)

    try:
        append_log(project_id, "[build] Creating virtual environment")
        result = subprocess.run([sys.executable, "-m", "venv", "--clear", str(venv_dir)], capture_output=True, text=True, cwd=repo, env=build_env)
        append_log(project_id, (result.stdout + result.stderr)[-2500:])
        if result.returncode != 0:
            fallback = subprocess.run(
                [sys.executable, "-m", "venv", "--clear", "--without-pip", "--system-site-packages", str(venv_dir)],
                capture_output=True,
                text=True,
                cwd=repo,
                env=build_env,
            )
            append_log(project_id, (fallback.stdout + fallback.stderr)[-2500:])
            if fallback.returncode != 0:
                raise RuntimeError("Virtual environment creation failed")

        env_example = repo / ".env.example"
        env_file = repo / ".env"
        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            append_log(project_id, "[build] Created .env from .env.example")

        append_log(project_id, "[build] Installing requirements")
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            capture_output=True,
            text=True,
            cwd=repo,
            env=build_env,
            timeout=600,
        )
        append_log(project_id, (result.stdout[-3000:] + result.stderr[-1500:]))
        if result.returncode != 0:
            raise RuntimeError("pip install failed")

        append_log(project_id, "[build] Creating database tables")
        env = _subprocess_env(cwd=repo, extra={"AUTO_CREATE_TABLES": "1", "PYTHONPATH": str(repo)})
        result = subprocess.run(
            [
                str(python_exe),
                "-c",
                "import os; os.environ['AUTO_CREATE_TABLES']='1'; from app.db import engine, Base; import app.models; Base.metadata.create_all(bind=engine); print('Tables created')",
            ],
            capture_output=True,
            text=True,
            cwd=repo,
            env=env,
            timeout=60,
        )
        append_log(project_id, (result.stdout + result.stderr)[-2500:])

        append_log(project_id, "[build] Seeding database")
        from builder.seed_runner import run_seed

        seed_ok, seed_output = run_seed(
            repo,
            str(python_exe),
            project_data=data,
            extra_env=_subprocess_env(cwd=repo),
            timeout=120,
            retry_with_repair=False,
        )
        if seed_output:
            append_log(project_id, seed_output[-3500:])

        append_log(project_id, "[build] Running automatic backend/runtime validation and self-healing")
        run_tdd_pass(project_id, str(repo), data)

        seed_ok, seed_output = run_seed(
            repo,
            str(python_exe),
            project_data=data,
            extra_env=_subprocess_env(cwd=repo),
            timeout=120,
            retry_with_repair=False,
        )
        if seed_output:
            append_log(project_id, seed_output[-3500:])
        final_issues = validate_before_serve(str(repo))
        for issue in final_issues:
            append_log(project_id, f"[validate:error] {issue}")

        build_ok = bool(seed_ok and not final_issues and data.get("tdd_passed"))
        data["build_done"] = build_ok
        data["seed_ok"] = bool(seed_ok)
        data["validation_issues"] = final_issues
        data["build_log_tail"] = PROJECT_LOGS.get(project_id, [])[-100:]
        _save_checkpoint(project_id, data, "BUILD_AND_RUN")
        if not build_ok:
            _diagnose_and_store_recovery(
                project_id,
                data,
                "\n".join(PROJECT_LOGS.get(project_id, [])[-100:]),
                0,
                "BUILD_AND_RUN",
            )
            raise RuntimeError(
                "Generated app did not pass seed and source validation."
            )
        append_log(project_id, "[build] Complete")
        return project_summary(project_id, data, "BUILD_AND_RUN")
    except Exception as exc:
        data["build_done"] = False
        data["build_error"] = f"{type(exc).__name__}: {exc}"
        data["build_log_tail"] = PROJECT_LOGS.get(project_id, [])[-100:]
        _diagnose_and_store_recovery(
            project_id,
            data,
            "\n".join(PROJECT_LOGS.get(project_id, [])[-100:]),
            0,
            "BUILD_AND_RUN",
        )
        _save_checkpoint(project_id, data, "BUILD_AND_RUN")
        append_log(project_id, "[build:error] " + data["build_error"])
        append_log(project_id, traceback.format_exc()[-2000:])
        raise


def _is_process_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False


def stop_server(project_id: str | None = None) -> Dict[str, Any]:
    if project_id:
        _validate_project_id(project_id)
    stopped: List[int] = []
    saved_pid: int | None = None
    if project_id:
        try:
            saved_data, _ = load_checkpoint(project_id)
            saved_pid = saved_data.get("server_pid")
        except Exception:
            saved_pid = None

    if project_id and project_id in SERVER_PROCESSES:
        proc = SERVER_PROCESSES.pop(project_id)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
            stopped.append(proc.pid)

    current_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
        try:
            if proc.info["pid"] == current_pid:
                continue
            cmdline = " ".join(proc.info.get("cmdline") or [])
            cwd = proc.info.get("cwd") or ""
            is_generated_app = "generated_apps" in cwd or "generated_apps" in cmdline
            belongs_to_project = not project_id or project_id in cwd or project_id in cmdline
            is_match = bool(saved_pid and proc.info["pid"] == saved_pid) or (
                is_generated_app and belongs_to_project
            )
            if is_match:
                proc.kill()
                stopped.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue

    if project_id:
        try:
            data, stage = load_checkpoint(project_id)
            data.pop("server_pid", None)
            _save_checkpoint(project_id, data, stage)
        except Exception:
            pass
        append_log(project_id, "[server] Stopped")
    return {"stopped": stopped}


def start_server(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    if not data.get("build_done"):
        raise ValueError("Build the generated app before starting the server.")
    repo = Path(data.get("repo_path", ""))
    if not repo.exists():
        raise ValueError("Generated repository not found.")
    validation_issues = validate_before_serve(str(repo))
    if validation_issues:
        raise RuntimeError(
            "Server start blocked by source validation: "
            + "; ".join(validation_issues[:10])
        )
    stop_server(project_id)
    time.sleep(1)
    port = get_project_port(project_id)
    venv_dir = repo / ".venv"
    uvicorn_exe = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("uvicorn.exe" if sys.platform == "win32" else "uvicorn")
    if not uvicorn_exe.exists():
        raise ValueError(f"Uvicorn not found at {uvicorn_exe}. Run build first.")
    if not (repo / "app" / "main.py").exists():
        raise ValueError("app/main.py not found. Code generation may have failed.")
    env = _subprocess_env(cwd=repo, extra={"PYTHONPATH": str(repo)})
    proc = subprocess.Popen(
        [str(uvicorn_exe), "app.main:app", "--reload", "--port", str(port), "--host", "127.0.0.1"],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    SERVER_PROCESSES[project_id] = proc
    time.sleep(3)
    if proc.poll() is not None:
        _, stderr = proc.communicate(timeout=1)
        raise RuntimeError(f"Server failed to start: {stderr[-2000:]}")
    data["server_pid"] = proc.pid
    _save_checkpoint(project_id, data, "BUILD_AND_RUN")
    append_log(project_id, f"[server] Started http://127.0.0.1:{port} pid={proc.pid}")
    return server_status(project_id)


def server_status(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    port = get_project_port(project_id)
    proc = SERVER_PROCESSES.get(project_id)
    running = bool(proc and proc.poll() is None)
    saved_pid = data.get("server_pid")
    if not running and saved_pid:
        running = _is_process_running(saved_pid)
    return {
        "project_id": project_id,
        "running": running,
        "pid": proc.pid if proc and proc.poll() is None else saved_pid,
        "port": port,
        "url": f"http://127.0.0.1:{port}",
        "docs_url": f"http://127.0.0.1:{port}/docs",
        "redoc_url": f"http://127.0.0.1:{port}/redoc",
        "health_url": f"http://127.0.0.1:{port}/health",
        "repo_path": data.get("repo_path"),
    }


def ollama_status() -> Dict[str, Any]:
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        response.raise_for_status()
        payload = response.json()
        models = [item.get("name") for item in payload.get("models", [])]
        mem = psutil.virtual_memory()
        return {
            "online": True,
            "models": models,
            "ram_percent": mem.percent,
            "ram_warning": mem.percent >= 80,
        }
    except Exception as exc:
        return {"online": False, "models": [], "error": str(exc), "ram_percent": psutil.virtual_memory().percent}


def size_report() -> dict:
    return get_project_size_report(ROOT_DIR)


def cleanup_system(keep_apps: int, keep_checkpoints: int) -> dict:
    return full_cleanup(ROOT_DIR, keep_latest_apps=keep_apps, keep_latest_checkpoints=keep_checkpoints)


def artifact_path(project_id: str, artifact_name: str) -> Path:
    _validate_project_id(project_id)
    mapping = {
        "requirements": CHECKPOINTS_DIR / project_id / "requirements.json",
        "srs": CHECKPOINTS_DIR / project_id / "srs.md",
        "blueprint": CHECKPOINTS_DIR / project_id / "blueprint.json",
        "manifest": CHECKPOINTS_DIR / project_id / "manifest.json",
        "analysis": CHECKPOINTS_DIR / project_id / "analysis.md",
    }
    if artifact_name not in mapping:
        raise ValueError("Unknown artifact.")
    return mapping[artifact_name]


def generate_post_analysis(project_id: str) -> Dict[str, Any]:
    data, _ = load_checkpoint(project_id)
    if not data.get("build_done"):
        raise ValueError("Build the project before post-analysis.")
    settings = load_settings()
    payload = {
        "plain_text_description": data.get("plain_text"),
        "cleaned_spec": data.get("cleaned_spec"),
        "requirements": data.get("requirements"),
        "user_stories": data.get("user_stories"),
        "architecture": data.get("architecture"),
        "data_model": data.get("data_model"),
        "srs_document_preview": (data.get("srs_document") or "")[:6000],
        "repo_path": data.get("repo_path"),
        "generated_project_snapshot": collect_generated_project_snapshot(data.get("repo_path")),
        "build_done": data.get("build_done"),
        "tdd_passed": data.get("tdd_passed"),
        "tdd_history": data.get("tdd_history", []),
        "build_log_tail": PROJECT_LOGS.get(project_id, [])[-80:],
    }
    markdown = ask_llm(
        system=ANALYSIS_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        num_predict=6000,
        model=settings["model_architect"],
        num_ctx=settings["model_ctx_architect"],
        timeout_sec=settings["timeout_post_analysis_sec"],
        retries=1,
    )
    data["post_analysis"] = markdown
    project_dir = CHECKPOINTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "analysis.md").write_text(markdown, encoding="utf-8")
    _save_checkpoint(project_id, data, "POST_ANALYSIS")
    append_log(project_id, "[analysis] Saved analysis.md")
    return project_summary(project_id, data, "POST_ANALYSIS")
