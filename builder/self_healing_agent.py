"""
Self-Healing Agent
==================
A true agentic AI system for autonomous debugging and repair of generated FastAPI web applications.

Capabilities:
  - Multi-phase root cause analysis with escalation
  - Persistent state tracking across healing cycles
  - Code backup and rollback mechanisms
  - Intelligent error pattern recognition
  - Phase-based healing (syntax → imports → schemas → routes → auth → integration → e2e)
  - Detailed healing reports with confidence scoring
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Phase Definitions ─────────────────────────────────────────────────────────
HEALING_PHASES = [
    {
        "name": "syntax",
        "label": "🔍 Phase 1: Syntax & Structure",
        "description": "Check Python syntax, file structure, and basic imports",
        "max_cycles": 3,
        "severity": "critical",
    },
    {
        "name": "imports",
        "label": "🔧 Phase 2: Imports & Dependencies",
        "description": "Fix missing imports, module paths, and package dependencies",
        "max_cycles": 3,
        "severity": "critical",
    },
    {
        "name": "schemas",
        "label": "📐 Phase 3: Schemas & Models",
        "description": "Align Pydantic schemas with SQLAlchemy models and DB constraints",
        "max_cycles": 4,
        "severity": "high",
    },
    {
        "name": "routes",
        "label": "🛣️ Phase 4: Routes & Registration",
        "description": "Fix route definitions, path matching, and router registration",
        "max_cycles": 4,
        "severity": "high",
    },
    {
        "name": "auth",
        "label": "🔐 Phase 5: Authentication & Authorization",
        "description": "Fix JWT auth, dependency injection, role checks, public/protected routes",
        "max_cycles": 5,
        "severity": "high",
    },
    {
        "name": "integration",
        "label": "🔄 Phase 6: Integration Testing",
        "description": "Fix end-to-end flows: register → login → CRUD → UI pages",
        "max_cycles": 5,
        "severity": "medium",
    },
    {
        "name": "e2e",
        "label": "🎯 Phase 7: End-to-End Validation",
        "description": "Final comprehensive healing pass for remaining edge cases",
        "max_cycles": 3,
        "severity": "low",
    },
]

# Known error patterns for fast classification
ERROR_PATTERNS = [
    {
        "pattern": r"SyntaxError",
        "phase": "syntax",
        "severity": "critical",
        "description": "Python syntax error in source file",
    },
    {
        "pattern": r"IndentationError",
        "phase": "syntax",
        "severity": "critical",
        "description": "Inconsistent indentation",
    },
    {
        "pattern": r"ModuleNotFoundError|ImportError",
        "phase": "imports",
        "severity": "critical",
        "description": "Missing module or import",
    },
    {
        "pattern": r"pydantic.*validation|ValidationError",
        "phase": "schemas",
        "severity": "high",
        "description": "Pydantic schema validation error",
    },
    {
        "pattern": r"sqlalchemy.*error|IntegrityError|OperationalError",
        "phase": "schemas",
        "severity": "high",
        "description": "SQLAlchemy/database error",
    },
    {
        "pattern": r"405 Method Not Allowed|404 Not Found",
        "phase": "routes",
        "severity": "high",
        "description": "HTTP method or route not found",
    },
    {
        "pattern": r"401 Unauthorized|403 Forbidden",
        "phase": "auth",
        "severity": "high",
        "description": "Authentication/authorization error",
    },
    {
        "pattern": r"AttributeError.*NoneType",
        "phase": "integration",
        "severity": "medium",
        "description": "NoneType attribute access",
    },
    {
        "pattern": r"KeyError",
        "phase": "routes",
        "severity": "medium",
        "description": "Missing key in response/schema",
    },
    {
        "pattern": r"TypeError",
        "phase": "schemas",
        "severity": "medium",
        "description": "Type mismatch",
    },
    {
        "pattern": r"ValueError",
        "phase": "integration",
        "severity": "medium",
        "description": "Value error in processing",
    },
    {
        "pattern": r"ConnectionRefusedError|ConnectionError",
        "phase": "integration",
        "severity": "critical",
        "description": "Connection refused - server not running",
    },
    {
        "pattern": r"TimeoutError|timeout",
        "phase": "integration",
        "severity": "medium",
        "description": "Operation timed out",
    },
    {
        "pattern": r"AssertionError|assert",
        "phase": "e2e",
        "severity": "low",
        "description": "Test assertion failure",
    },
]


class HealingState:
    """Persistent state tracker for the self-healing agent."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.backup_dir = self.project_dir / ".healing_backups"
        self.state_file = self.project_dir / ".healing_state.json"
        self._state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "project_id": "",
            "healing_id": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "current_phase": 0,
            "current_cycle": 0,
            "phases": {},
            "healing_history": [],
            "backup_count": 0,
            "files_modified": [],
            "errors_seen": [],
            "patterns_matched": [],
            "confidence": 0.0,
            "status": "active",
        }

    def save(self):
        self._state["updated_at"] = datetime.now().isoformat()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def update_phase(self, phase_index: int, cycle: int):
        phase_name = HEALING_PHASES[phase_index]["name"]
        if phase_name not in self._state["phases"]:
            self._state["phases"][phase_name] = {
                "started_at": datetime.now().isoformat(),
                "cycles": 0,
                "errors_fixed": 0,
                "status": "active",
            }
        self._state["phases"][phase_name]["cycles"] = cycle
        self._state["current_phase"] = phase_index
        self._state["current_cycle"] = cycle
        self.save()

    def record_healing(self, entry: Dict[str, Any]):
        self._state["healing_history"].append({
            **entry,
            "timestamp": datetime.now().isoformat(),
        })
        self.save()

    def record_backup(self, file_rel: str):
        self._state["backup_count"] += 1
        if file_rel not in self._state["files_modified"]:
            self._state["files_modified"].append(file_rel)
        self.save()

    def record_error(self, error_text: str, phase: str):
        self._state["errors_seen"].append({
            "phase": phase,
            "text": error_text[:500],
            "timestamp": datetime.now().isoformat(),
        })
        # Check for known patterns
        for pattern in ERROR_PATTERNS:
            if re.search(pattern["pattern"], error_text, re.IGNORECASE):
                match_info = {**pattern, "error_snippet": error_text[:200]}
                if match_info not in self._state["patterns_matched"]:
                    self._state["patterns_matched"].append(match_info)
        self.save()

    def set_confidence(self, score: float):
        self._state["confidence"] = max(0.0, min(1.0, score))
        self.save()

    def mark_complete(self, success: bool):
        self._state["status"] = "completed" if success else "failed"
        self.save()

    @property
    def current_phase_name(self) -> str:
        idx = self._state["current_phase"]
        if idx < len(HEALING_PHASES):
            return HEALING_PHASES[idx]["name"]
        return "completed"

    @property
    def is_stuck(self) -> bool:
        """Detect if we're stuck in a loop (same errors repeating)."""
        if len(self._state["healing_history"]) < 3:
            return False
        recent = self._state["healing_history"][-3:]
        # Check if the same files keep getting modified
        files_set = set()
        for entry in recent:
            for f in entry.get("files_changed", []):
                files_set.add(f)
        # If we modified the same file 3 times in a row, we might be stuck
        if len(files_set) <= 1 and len(recent) == 3:
            return True
        return False


class SelfHealingAgent:
    """
    True agentic self-healing system for FastAPI web applications.
    
    Features:
    - Multi-phase escalation with increasing aggressiveness
    - Intelligent error pattern recognition
    - Code backup and rollback
    - Persistent state tracking
    - Adaptive healing strategies based on error patterns
    """

    def __init__(
        self,
        project_dir: str,
        ask_llm_fn: Callable,
        progress_callback: Optional[Callable[[str], None]] = None,
        max_total_cycles: int = 27,
        project_context: Optional[Dict[str, Any]] = None,
    ):
        self.project_dir = Path(project_dir)
        self.ask_llm = ask_llm_fn
        self.progress = progress_callback or (lambda msg: print(msg))
        self.max_total_cycles = max_total_cycles
        self.project_context = project_context or {}
        self.project_id = (
            str(self.project_context.get("project_id") or "").strip()
            or (self.project_dir.parent.name if self.project_dir.name.lower() == "v1" else self.project_dir.name)
        )
        self.state = HealingState(self.project_dir)
        self.phase_healers = {
            "syntax": self._heal_syntax,
            "imports": self._heal_imports,
            "schemas": self._heal_schemas,
            "routes": self._heal_routes,
            "auth": self._heal_auth,
            "integration": self._heal_integration,
            "e2e": self._heal_e2e,
        }

    def log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.progress(f"[🤖 Self-Healing {timestamp}] {msg}")

    def log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_msg = str(msg).encode(encoding, errors="replace").decode(encoding)
        self.progress(f"[Self-Healing {timestamp}] {safe_msg}")

    def run_healing_cycle(self, test_output: str) -> Dict[str, Any]:
        """
        Run one complete healing cycle.
        
        Args:
            test_output: Full pytest output from the failing test run
            
        Returns:
            Dict with healing results
        """
        # Classify the error
        phase_name, severity = self._classify_error(test_output)
        self.state.record_error(test_output, phase_name)
        
        # Determine which phase to use
        phase_idx = self._get_phase_index(phase_name)
        phase_info = HEALING_PHASES[phase_idx]
        current_cycle = self.state._state["phases"].get(phase_name, {}).get("cycles", 0) + 1
        
        self.log(f"Error classified as: {phase_info['label']} (cycle {current_cycle}/{phase_info['max_cycles']})")
        self.state.update_phase(phase_idx, current_cycle)
        
        # Check if stuck
        if self.state.is_stuck:
            self.log("⚠️ Healing loop detected! Escalating to next phase...")
            return self._escalate_phase(test_output)
        
        # Get the healer for this phase
        healer = self.phase_healers.get(phase_name, self._heal_integration)
        
        # Backup current files
        self._backup_current_files()
        
        # Execute healing
        try:
            result = healer(test_output, phase_info, current_cycle)
            result["phase"] = phase_name
            result["cycle"] = current_cycle
            self.state.record_healing(result)
            
            # Update confidence
            if result.get("success"):
                current_confidence = self.state._state.get("confidence", 0.0)
                self.state.set_confidence(min(1.0, current_confidence + 0.15))
            else:
                current_confidence = self.state._state.get("confidence", 0.0)
                self.state.set_confidence(max(0.0, current_confidence - 0.05))
            
            return result
        except Exception as e:
            self.log(f"❌ Healing phase failed with exception: {e}")
            return {
                "phase": phase_name,
                "cycle": current_cycle,
                "success": False,
                "error": str(e),
                "rewrites": [],
                "analysis": f"Exception during healing: {e}",
            }

    def _classify_error(self, test_output: str) -> Tuple[str, str]:
        """Classify the error type using known patterns and LLM analysis."""
        # First pass: quick pattern matching
        for pattern in ERROR_PATTERNS:
            if re.search(pattern["pattern"], test_output, re.IGNORECASE):
                return pattern["phase"], pattern["severity"]
        
        # Second pass: analyze specific test failure patterns
        if "FAILED" in test_output and "assert" in test_output:
            if "401" in test_output or "403" in test_output:
                return "auth", "high"
            if "404" in test_output:
                return "routes", "high"
            if "422" in test_output or "400" in test_output:
                return "schemas", "high"
            return "e2e", "low"
        
        # Default: start with syntax and escalate
        if self.state._state["current_phase"] == 0:
            return "syntax", "critical"
        return self.state.current_phase_name, "medium"

    def _get_phase_index(self, phase_name: str) -> int:
        """Get the index of a phase by name."""
        for i, phase in enumerate(HEALING_PHASES):
            if phase["name"] == phase_name:
                return i
        return 0

    def _backup_current_files(self):
        """Create backup copies of all source files before healing."""
        backup_dir = self.state.backup_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cycle_backup = backup_dir / f"before_cycle_{timestamp}"
        cycle_backup.mkdir(parents=True, exist_ok=True)
        
        source_files = [
            "app/main.py",
            "app/models.py",
            "app/schemas.py",
            "app/auth.py",
            "app/db.py",
            "app/deps.py",
            "app/routers/auth.py",
            "app/routers/generic_crud.py",
            "app/__init__.py",
            "app/routers/__init__.py",
            "seed.py",
        ]
        
        backed_up = []
        for rel_path in source_files:
            src = self.project_dir / rel_path
            if src.exists():
                dst = cycle_backup / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                backed_up.append(rel_path)
                self.state.record_backup(rel_path)
        
        # Clean old backups (keep last 10)
        all_backups = sorted(backup_dir.glob("before_cycle_*"))
        while len(all_backups) > 10:
            shutil.rmtree(all_backups[0])
            all_backups = all_backups[1:]
        
        self.log(f"📦 Backed up {len(backed_up)} files to {cycle_backup.name}")

    def _read_source_files(self) -> Dict[str, str]:
        """Read all source files into a dictionary."""
        source_files = [
            "app/main.py",
            "app/models.py",
            "app/schemas.py",
            "app/auth.py",
            "app/db.py",
            "app/deps.py",
            "app/routers/auth.py",
            "app/routers/generic_crud.py",
            "app/__init__.py",
            "app/routers/__init__.py",
            "seed.py",
            # NOTE: requirements.txt excluded - it's an infrastructure file from Jinja2 template
            # Self-healing should NEVER modify infrastructure files (requirements, .env, db.py, auth.py, deps.py)
        ]
        result = {}
        for rel_path in source_files:
            src = self.project_dir / rel_path
            if src.exists():
                result[rel_path] = src.read_text(encoding="utf-8")
        return result

    def _build_healing_prompt(
        self,
        phase_info: Dict[str, Any],
        test_output: str,
        source_files: Dict[str, str],
        cycle: int,
        escalation_level: int = 0,
    ) -> str:
        """Build a comprehensive healing prompt for the LLM."""
        
        # Phase-specific instructions
        phase_instructions = {
            "syntax": """
## PHASE: Syntax & Structure Healing
Fix Python syntax errors, indentation, and basic structural issues.
- Check for missing colons, unmatched brackets, invalid syntax
- Validate that all class/function definitions have correct indentation
- Ensure all files parse correctly with compile()
""",
            "imports": """
## PHASE: Imports & Dependencies Healing
Fix missing imports, circular imports, and dependency issues.
- Add missing import statements
- Fix module paths and package references
- **DO NOT modify requirements.txt** - it's an infrastructure file with all needed packages
- Resolve circular import issues by moving imports inside functions
- All Python packages are already installed - focus on fixing import statements only
""",
            "schemas": """
## PHASE: Schemas & Models Healing
Align Pydantic schemas with SQLAlchemy models.
- Ensure every model field has a corresponding schema field
- Fix type mismatches between schemas, models, and DB
- Add missing fields (created_at, updated_at, etc.)
- Ensure foreign keys are properly defined
- Check nullable/required consistency
""",
            "routes": """
## PHASE: Routes & Registration Healing
Fix route definitions and router registration.
- Ensure all route handlers are properly registered with @router or @app decorators
- Verify include_router() calls in main.py
- Fix HTTP method mismatches (POST vs GET vs PUT vs DELETE)
- Ensure path parameters match function signature
- Add missing route handlers
""",
            "auth": """
## PHASE: Authentication & Authorization Healing
Fix JWT auth, dependencies, and role-based access.
- Public routes must NOT have get_current_user dependency
- Protected routes MUST have get_current_user dependency
- Admin routes MUST have require_admin dependency
- Verify token creation/validation in auth.py
- Ensure login returns {"access_token", "token_type"} 
- Ensure register creates user with hashed password
""",
            "integration": """
## PHASE: Integration Testing Healing
Fix end-to-end flow issues between components.
- Ensure register → login → CRUD flow works end-to-end
- Fix response format that tests expect
- Ensure seed.py creates admin user for testing
- Fix database session handling
""",
            "e2e": """
## PHASE: End-to-End Validation Healing
Final comprehensive fixes for remaining test failures.
- Fix edge cases in data validation
- Ensure consistent error response format
- Handle all boundary conditions
- Fix any remaining assertion failures
""",
        }
        
        instructions = phase_instructions.get(
            phase_info["name"],
            "Fix the errors in the test output by rewriting the necessary source files."
        )
        
        # Add escalation instructions
        escalation_instructions = ""
        if escalation_level >= 1:
            escalation_instructions = """
### ESCALATION LEVEL 1: More aggressive healing
- If a file has multiple issues, rewrite the ENTIRE file rather than patching
- Check for missing functions entirely and add them
- Ensure all possible error paths are handled
"""
        if escalation_level >= 2:
            escalation_instructions += """
### ESCALATION LEVEL 2: Maximum aggressiveness
- Rewrite ALL related files completely to ensure consistency
- Add comprehensive error handling
- Double-check all imports and dependencies
- Verify the complete request flow (HTTP → route → schema → model → DB → response)
"""
        if escalation_level >= 3:
            escalation_instructions += """
### ESCALATION LEVEL 3: Emergency healing
- Complete rewrite of the affected system to ensure all tests pass
- Simplify complex logic that may have hidden bugs
- Add more defensive programming
- Ensure every function has proper type hints and docstrings
"""
        
        # Build context about what we've tried
        history_context = ""
        history = self.state._state["healing_history"]
        if history:
            recent = history[-3:]
            history_context = "\n".join(
                f"  - Cycle {h.get('cycle', '?')}: {h.get('analysis', 'No analysis')[:100]}"
                for h in recent
            )
        
        def excerpt(content: str, limit: int = 6000) -> str:
            if len(content) <= limit:
                return content
            return content[:4500] + "\n# ... middle omitted ...\n" + content[-1400:]

        budgeted_sources = {
            path: excerpt(content)
            for path, content in source_files.items()
        }
        context = self.project_context or {}
        project_summary = {
            "cleaned_spec": context.get("cleaned_spec", {}),
            "architecture": {
                "roles": (context.get("architecture", {}) or {}).get("roles", []),
                "pages": (context.get("architecture", {}) or {}).get("pages", []),
                "endpoints": (context.get("architecture", {}) or {}).get("endpoints", []),
            },
            "data_model": context.get("data_model", {}),
            "source_policy": "plain HTML/CSS/JavaScript; Jinja is forbidden",
        }

        prompt = f"""You are a world-class Python/FastAPI debugging expert. Fix the failing tests by rewriting ONLY the necessary source files.

## Cycle {cycle} | Phase: {phase_info['label']}
Severity: {phase_info['severity']}
Max cycles for this phase: {phase_info['max_cycles']}

{instructions}

{escalation_instructions}

## Recent Healing History (last 3 cycles):
{history_context or '  - None yet'}

## Project Contract:
```json
{json.dumps(project_summary, indent=2, default=str)[:10000]}
```

## Failing Test Output:
```
{test_output[-4000:]}
```

## Current Source Files:
```json
{json.dumps(budgeted_sources, indent=2, default=str)[:28000]}
```

## CRITICAL RULES:
1. Output ONLY valid JSON. No markdown. No explanations outside the JSON.
2. NEVER modify test files (tests/*.py). Fix SOURCE code only.
3. "content" field MUST contain the COMPLETE file (top to bottom, all imports, all functions).
4. Only include files that actually need changes.
5. Fix ROOT CAUSE, not just symptom.
6. If you cannot determine the fix, set "analysis" to "UNCLEAR" and provide best guess anyway.
7. On cycle 3+, rewrite entire files instead of patching.
8. Preserve plain source files. Never add Jinja expressions or .j2 files.
9. Auth, dependencies, models, schemas, routes, seed data, and frontend files
   may all be repaired when the failing request path requires it.

## OUTPUT SCHEMA:
{{
    "analysis": "Brief root cause description and what was changed",
    "confidence": 0.0-1.0,
    "rewrites": [
        {{
            "file": "app/auth.py",
            "reason": "Why this file needs changing",
            "content": "# COMPLETE FILE CONTENT - every import, every function, every line"
        }}
    ]
}}
"""
        return prompt

    def _parse_healing_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse LLM healing response into structured format."""
        try:
            # Try direct JSON parse
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*\n(.+?)\n```', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object directly
        json_match = re.search(r'(\{[\s\S]*"analysis"[\s\S]*"rewrites"[\s\S]*\})', raw_response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Fallback: return raw text as analysis
        return {
            "analysis": raw_response[:500] if raw_response else "Failed to parse healing response",
            "confidence": 0.0,
            "rewrites": [],
        }

    def _apply_fixes(self, rewrites: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply file rewrites from healing response."""
        applied = []
        failed = []
        
        # Dependency/environment manifests are managed by the build service.
        PROTECTED_INFRASTRUCTURE = {
            "requirements.txt",
            ".env",
            ".env.example",
        }
        
        for rewrite in rewrites:
            file_rel = rewrite.get("file", "")
            content = rewrite.get("content", "")
            
            if not file_rel or not content:
                failed.append(f"Invalid rewrite entry: {file_rel}")
                continue
            
            # PROTECTION: Block modifications to infrastructure files
            normalized = Path(file_rel)
            if (
                file_rel in PROTECTED_INFRASTRUCTURE
                or normalized.is_absolute()
                or ".." in normalized.parts
                or normalized.parts[:1] == ("tests",)
            ):
                self.log(f"  ⚠️  Skipped: {file_rel} - Infrastructure file protected from modification")
                continue
            
            target = self.project_dir / file_rel
            
            try:
                # Validate Python files by compiling
                if file_rel.endswith(".py"):
                    try:
                        compile(content, file_rel, "exec")
                    except SyntaxError as se:
                        failed.append(f"Syntax error in {file_rel}: {se}")
                        continue
                if file_rel.endswith(".html") and any(
                    marker in content for marker in ("{{", "{%", "{#")
                ):
                    failed.append(f"Template syntax is forbidden in {file_rel}")
                    continue
                
                # Write the file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                applied.append(file_rel)
                self.log(f"  ✅ Fixed: {file_rel} - {rewrite.get('reason', '')}")
                
            except Exception as e:
                failed.append(f"Failed to write {file_rel}: {e}")
                self.log(f"  ❌ Failed: {file_rel} - {e}")
        
        return {
            "applied": applied,
            "failed": failed,
            "success": len(applied) > 0 or len(failed) == 0,
        }

    def _heal_syntax(
        self, test_output: str, phase_info: Dict, cycle: int
    ) -> Dict[str, Any]:
        """Phase 1: Fix syntax errors."""
        source_files = self._read_source_files()
        prompt = self._build_healing_prompt(phase_info, test_output, source_files, cycle)
        
        raw_response = self.ask_llm(
            system="You are a Python syntax expert. Fix ONLY syntax errors in the provided files.",
            user=prompt,
            num_predict=4000,
        )
        
        result = self._parse_healing_response(raw_response)
        fix_result = self._apply_fixes(result.get("rewrites", []))
        
        return {
            "success": fix_result["success"],
            "analysis": result.get("analysis", "Syntax healing applied"),
            "confidence": result.get("confidence", 0.5),
            "files_changed": fix_result["applied"],
            "errors": fix_result["failed"],
            "rewrites": result.get("rewrites", []),
        }

    def _heal_imports(
        self, test_output: str, phase_info: Dict, cycle: int
    ) -> Dict[str, Any]:
        """Phase 2: Fix import errors."""
        source_files = self._read_source_files()
        escalation = min(cycle, 3)
        prompt = self._build_healing_prompt(phase_info, test_output, source_files, cycle, escalation)
        
        raw_response = self.ask_llm(
            system="You are a Python import/module expert. Fix all import errors and missing dependencies.",
            user=prompt,
            num_predict=4000,
        )
        
        result = self._parse_healing_response(raw_response)
        fix_result = self._apply_fixes(result.get("rewrites", []))
        
        return {
            "success": fix_result["success"],
            "analysis": result.get("analysis", "Import healing applied"),
            "confidence": result.get("confidence", 0.5),
            "files_changed": fix_result["applied"],
            "errors": fix_result["failed"],
            "rewrites": result.get("rewrites", []),
        }

    def _heal_schemas(
        self, test_output: str, phase_info: Dict, cycle: int
    ) -> Dict[str, Any]:
        """Phase 3: Fix schema/model alignment."""
        source_files = self._read_source_files()
        escalation = min(cycle, 3)
        prompt = self._build_healing_prompt(phase_info, test_output, source_files, cycle, escalation)
        
        raw_response = self.ask_llm(
            system="You are a FastAPI/SQLAlchemy schema expert. Fix ALL model-schema alignment issues.",
            user=prompt,
            num_predict=5000,
        )
        
        result = self._parse_healing_response(raw_response)
        fix_result = self._apply_fixes(result.get("rewrites", []))
        
        return {
            "success": fix_result["success"],
            "analysis": result.get("analysis", "Schema healing applied"),
            "confidence": result.get("confidence", 0.5),
            "files_changed": fix_result["applied"],
            "errors": fix_result["failed"],
            "rewrites": result.get("rewrites", []),
        }

    def _heal_routes(
        self, test_output: str, phase_info: Dict, cycle: int
    ) -> Dict[str, Any]:
        """Phase 4: Fix route registration."""
        source_files = self._read_source_files()
        escalation = min(cycle, 3)
        prompt = self._build_healing_prompt(phase_info, test_output, source_files, cycle, escalation)
        
        raw_response = self.ask_llm(
            system="You are a FastAPI routing expert. Fix ALL route definitions and router registrations.",
            user=prompt,
            num_predict=5000,
        )
        
        result = self._parse_healing_response(raw_response)
        fix_result = self._apply_fixes(result.get("rewrites", []))
        
        return {
            "success": fix_result["success"],
            "analysis": result.get("analysis", "Route healing applied"),
            "confidence": result.get("confidence", 0.5),
            "files_changed": fix_result["applied"],
            "errors": fix_result["failed"],
            "rewrites": result.get("rewrites", []),
        }

    def _heal_auth(
        self, test_output: str, phase_info: Dict, cycle: int
    ) -> Dict[str, Any]:
        """Phase 5: Fix authentication/authorization."""
        source_files = self._read_source_files()
        escalation = min(cycle, 3)
        prompt = self._build_healing_prompt(phase_info, test_output, source_files, cycle, escalation)
        
        raw_response = self.ask_llm(
            system="You are a FastAPI security/auth expert. Fix ALL authentication and authorization issues.",
            user=prompt,
            num_predict=6000,
        )
        
        result = self._parse_healing_response(raw_response)
        fix_result = self._apply_fixes(result.get("rewrites", []))
        
        return {
            "success": fix_result["success"],
            "analysis": result.get("analysis", "Auth healing applied"),
            "confidence": result.get("confidence", 0.5),
            "files_changed": fix_result["applied"],
            "errors": fix_result["failed"],
            "rewrites": result.get("rewrites", []),
        }

    def _heal_integration(
        self, test_output: str, phase_info: Dict, cycle: int
    ) -> Dict[str, Any]:
        """Phase 6: Fix integration/flow issues."""
        source_files = self._read_source_files()
        escalation = min(cycle, 3)
        prompt = self._build_healing_prompt(phase_info, test_output, source_files, cycle, escalation)
        
        raw_response = self.ask_llm(
            system="You are a Full-Stack FastAPI integration expert. Fix ALL end-to-end flow issues.",
            user=prompt,
            num_predict=6000,
        )
        
        result = self._parse_healing_response(raw_response)
        fix_result = self._apply_fixes(result.get("rewrites", []))
        
        return {
            "success": fix_result["success"],
            "analysis": result.get("analysis", "Integration healing applied"),
            "confidence": result.get("confidence", 0.5),
            "files_changed": fix_result["applied"],
            "errors": fix_result["failed"],
            "rewrites": result.get("rewrites", []),
        }

    def _heal_e2e(
        self, test_output: str, phase_info: Dict, cycle: int
    ) -> Dict[str, Any]:
        """Phase 7: Final e2e healing."""
        source_files = self._read_source_files()
        escalation = min(cycle + 1, 4)  # Higher escalation for e2e
        prompt = self._build_healing_prompt(phase_info, test_output, source_files, cycle, escalation)
        
        raw_response = self.ask_llm(
            system="You are a Senior Full-Stack Architect. Perform FINAL comprehensive healing to ensure ALL tests pass.",
            user=prompt,
            num_predict=8000,
        )
        
        result = self._parse_healing_response(raw_response)
        fix_result = self._apply_fixes(result.get("rewrites", []))
        
        return {
            "success": fix_result["success"],
            "analysis": result.get("analysis", "E2E healing applied"),
            "confidence": result.get("confidence", 0.5),
            "files_changed": fix_result["applied"],
            "errors": fix_result["failed"],
            "rewrites": result.get("rewrites", []),
        }

    def _escalate_phase(self, test_output: str) -> Dict[str, Any]:
        """Escalate to next phase when stuck in current one."""
        current_idx = self.state._state["current_phase"]
        next_idx = min(current_idx + 1, len(HEALING_PHASES) - 1)
        
        if next_idx == current_idx:
            # Already at max phase - do aggressive e2e healing
            return self._heal_e2e(test_output, HEALING_PHASES[-1], 99)
        
        next_phase = HEALING_PHASES[next_idx]
        self.log(f"⬆️ Escalating to {next_phase['label']}")
        self.state.update_phase(next_idx, 1)
        
        healer = self.phase_healers.get(next_phase["name"], self._heal_integration)
        return healer(test_output, next_phase, 1)

    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive healing summary."""
        state = self.state._state
        phases_completed = sum(
            1 for p in state["phases"].values() if p.get("status") == "completed"
        )
        total_fixes = state.get("backup_count", 0)
        total_cycles = len(state.get("healing_history", []))
        
        return {
            "status": state["status"],
            "total_cycles": total_cycles,
            "phases_completed": phases_completed,
            "total_fixes": total_fixes,
            "files_modified": state.get("files_modified", []),
            "confidence": state.get("confidence", 0.0),
            "patterns_matched": len(state.get("patterns_matched", [])),
            "errors_analyzed": len(state.get("errors_seen", [])),
        }


def run_agentic_tdd(
    project_dir: str,
    ask_llm_fn: Callable,
    test_command: List[str],
    max_cycles: int = 27,
    progress_callback: Optional[Callable[[str], None]] = None,
    venv_python: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Run the full agentic TDD loop with self-healing.
    
    Args:
        project_dir: Path to the generated project
        ask_llm_fn: LLM function (system, user, num_predict) -> str
        test_command: List of args for pytest (e.g., ["-m", "pytest", "tests/", "-v"])
        max_cycles: Maximum total healing cycles
        progress_callback: Optional progress logging function
        venv_python: Path to venv Python executable
        env: Environment variables for subprocess
    
    Returns:
        Dict with final TDD results
    """
    project_path = Path(project_dir)
    agent = SelfHealingAgent(project_dir, ask_llm_fn, progress_callback)
    
    python_exe = venv_python or sys.executable
    agent.log(f"🚀 Starting Agentic TDD Loop (max {max_cycles} cycles)")
    agent.log(f"📁 Project: {project_dir}")
    agent.log(f"🐍 Python: {python_exe}")
    
    run_env = env or os.environ.copy()

    def _write_failure_report(last_output: str, cycles: int) -> Path:
        report_path = project_path / "RUNTIME_FAILURE_REPORT.txt"
        report_path.write_text(
            "Runtime Self-Healing Failure Report\n"
            "===================================\n\n"
            f"Project directory: {project_path}\n"
            f"Maximum cycles attempted: {cycles}\n\n"
            "Scope tested:\n"
            "- Database functionality: seeding, login/auth read, generated resource list APIs.\n"
            "- Buttons/forms: login/register submit JavaScript hooks and safe DOM lookups.\n"
            "- Pages loading: root app shell, login page, register page, and generated UI routes.\n\n"
            "Where the failure used to be:\n"
            "- Self-healing escalation called `self.phase_heaters`, but the class defines `self.phase_healers`.\n"
            "- Test setup installed pytest/httpx only, so generated apps could fail with `ModuleNotFoundError: fastapi` before runtime checks started.\n"
            "- Generated auth pages used unsafe global DOM variables such as `name.value`, which could break buttons at runtime.\n\n"
            "Runtime impact:\n"
            "- Tests could stop during import collection and never reach database, button, or page-load checks.\n"
            "- The healing loop could crash while escalating instead of applying a final fallback.\n"
            "- Users could open pages but submit buttons might not execute reliably.\n\n"
            "Last test output:\n"
            "-----------------\n"
            f"{last_output[-4000:]}\n",
            encoding="utf-8",
        )
        return report_path

    req_file = project_path / "requirements.txt"
    if req_file.exists():
        agent.log("Installing generated app requirements before tests...")
        dep_pr = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-q", "-r", str(req_file), "pytest", "pytest-asyncio", "httpx", "requests"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,
            env=run_env,
        )
        if dep_pr.returncode != 0:
            agent.log("Dependency install reported issues; tests will still run.")
            agent.log((dep_pr.stdout + "\n" + dep_pr.stderr)[-1500:])
    
    for cycle in range(1, max_cycles + 1):
        agent.log(f"\n{'='*60}")
        agent.log(f"🔄 COMPREHENSIVE HEALING CYCLE {cycle}/{max_cycles}")
        agent.log(f"{'='*60}")
        
        # Run tests
        agent.log("▶️ Running tests...")
        pr = None
        try:
            pr = subprocess.run(
                test_command,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=180,
                env=run_env,
            )
            test_output = pr.stdout + "\n" + pr.stderr
        except subprocess.TimeoutExpired:
            test_output = "TIMEOUT: Tests took longer than 180 seconds"
            agent.log("⏱️ Tests timed out")
        except Exception as e:
            test_output = f"ERROR running tests: {e}"
            agent.log(f"❌ Test execution error: {e}")
        
        # Output test result summary
        if pr is not None and pr.returncode == 0:
            agent.log("✅ ALL TESTS PASSED! 🎉")
            agent.state.mark_complete(True)
            
            # Record final state
            result = {
                "success": True,
                "total_cycles": cycle,
                "final_confidence": agent.state._state.get("confidence", 0.0),
                "summary": agent.get_summary(),
            }
            return result
        
        # Tests failed - count failures
        failed_count = test_output.count(" FAILED") + test_output.count(" ERROR")
        agent.log(f"❌ {failed_count} test(s) failing")
        
        # Show last part of test output
        tail = test_output[-1500:]
        agent.log(f"📋 Last test output:\n{tail}")
        
        # Run healing
        try:
            healing_result = agent.run_healing_cycle(test_output)
            
            if healing_result.get("success"):
                files_fixed = len(healing_result.get("files_changed", []))
                agent.log(f"🔧 Applied {files_fixed} file fix(es)")
            else:
                agent.log(f"⚠️ Healing had issues: {healing_result.get('analysis', 'Unknown')}")
                
        except Exception as heal_err:
            agent.log(f"❌ Healing exception: {heal_err}")
            agent.log(traceback.format_exc()[-1000:])
        
        # Check if we should give up
        if agent.state.is_stuck and cycle >= max_cycles - 2:
            agent.log("⚠️ Still stuck after maximum cycles. Performing final emergency healing...")
            emergency = agent._heal_e2e(test_output, HEALING_PHASES[-1], 99)
            agent.log(f"🚑 Emergency healing applied: {emergency.get('analysis', 'N/A')}")
    
    # Max cycles reached. Before giving up, check whether this looks like an
    # upstream architecture/data-model problem rather than only a code bug.
    agent.state.mark_complete(False)
    agent.log(f"Max cycles ({max_cycles}) reached without full pass.")
    diagnosis = None
    try:
        from builder.failure_classifier import classify_failure
        from builder.checkpoint_manager import load_checkpoint

        project_data, _ = load_checkpoint(agent.project_id)
        diagnosis = classify_failure(project_data, test_output, max_cycles)
        agent.log(
            "Failure diagnosis: "
            f"{diagnosis['category']} (confidence {diagnosis['confidence']}) - "
            f"{diagnosis['reason']}"
        )
    except Exception as diag_err:
        agent.log(f"Could not run failure diagnosis: {diag_err}")

    return {
        "success": False,
        "total_cycles": max_cycles,
        "final_confidence": agent.state._state.get("confidence", 0.0),
        "summary": agent.get_summary(),
        "last_test_output": test_output[-2000:],
        "diagnosis": diagnosis,
    }
