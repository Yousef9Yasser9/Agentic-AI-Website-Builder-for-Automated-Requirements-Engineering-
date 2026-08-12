"""Reliability report: scans saved checkpoints and reports the build-pass rate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STAGES = [
    "PLAIN_TEXT", "CLEANED_SPEC", "REQUIREMENTS", "USER_STORIES",
    "ARCHITECTURE", "DATA_MODEL", "SRS_DOCUMENTATION", "UI_SELECTION",
    "CODE_GENERATION", "BUILD_AND_RUN", "PREVIEW",
]
STAGE_INDEX = {name: i for i, name in enumerate(STAGES)}


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _looks_like_role_mismatch(pd: dict) -> bool:
    arch = pd.get("architecture") or {}
    dm = pd.get("data_model") or {}
    entities = {str(e.get("name", "")).lower().replace("_", "") for e in dm.get("entities", []) or []}
    roles = {str(r).strip().lower() for r in (arch.get("roles") or [])}
    for ep in arch.get("endpoints", []) or []:
        path = str(ep.get("path", "")).lower()
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        while parts and (parts[0] == "api" or (parts[0].startswith("v") and parts[0][1:].isdigit())):
            parts.pop(0)
        if not parts:
            continue
        seg = parts[0].replace("-", "").replace("_", "")
        seg_singular = seg[:-1] if seg.endswith("s") else seg
        if seg in {r + "s" for r in roles} or seg_singular in roles:
            if seg not in entities and seg_singular not in entities:
                return True
    return False


def analyze(checkpoints_dir: Path) -> dict:
    rows = []
    for cp_dir in sorted(p for p in checkpoints_dir.iterdir() if p.is_dir()):
        cp = _load(cp_dir / "checkpoint.json")
        if not cp:
            continue
        pd = cp.get("project_data", {}) or {}
        stage = str(cp.get("stage", "")).upper()
        reached = STAGE_INDEX.get(stage, -1)
        tdd = pd.get("tdd_passed")
        build = pd.get("build_done")
        rows.append({
            "id": cp_dir.name,
            "title": cp.get("project_title", "?"),
            "stage": stage,
            "stage_index": reached,
            "tdd_passed": tdd,
            "build_done": build,
            "passed": bool(tdd) and bool(build),
            "role_mismatch_suspected": _looks_like_role_mismatch(pd),
        })
    total = len(rows)
    reached_codegen = [r for r in rows if r["stage_index"] >= STAGE_INDEX["CODE_GENERATION"]]
    passed = [r for r in rows if r["passed"]]
    mismatch = [r for r in rows if r["role_mismatch_suspected"]]
    return {
        "total_projects": total,
        "reached_code_generation": len(reached_codegen),
        "passed_build_and_tests": len(passed),
        "build_pass_rate_pct": round(100 * len(passed) / total, 1) if total else 0.0,
        "pass_rate_of_those_that_reached_codegen_pct": (
            round(100 * len(passed) / len(reached_codegen), 1) if reached_codegen else 0.0
        ),
        "role_mismatch_suspected_count": len(mismatch),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoints", default="checkpoints")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    cp_dir = Path(args.checkpoints)
    if not cp_dir.is_dir():
        print(f"Checkpoints directory not found: {cp_dir}", file=sys.stderr)
        return 1
    report = analyze(cp_dir)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print("=" * 64)
    print("AI WEBSITE BUILDER — RELIABILITY REPORT")
    print("=" * 64)
    print(f"Projects analyzed            : {report['total_projects']}")
    print(f"Reached CODE_GENERATION      : {report['reached_code_generation']}")
    print(f"Passed build + runtime tests : {report['passed_build_and_tests']}")
    print(f"Build-pass rate (overall)    : {report['build_pass_rate_pct']}%")
    print(f"Pass rate (of those at code) : {report['pass_rate_of_those_that_reached_codegen_pct']}%")
    print(f"Role-mismatch suspected      : {report['role_mismatch_suspected_count']}")
    print("-" * 64)
    print(f"{'app':36} {'stage':18} pass")
    print("-" * 64)
    for r in report["rows"]:
        flag = " role-mismatch" if r["role_mismatch_suspected"] else ""
        print(f"{r['title'][:35]:36} {r['stage'][:17]:18} {'PASS' if r['passed'] else '.'}{flag}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
