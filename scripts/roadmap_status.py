"""Generate computed ROADMAP.md from capabilities.json and CI evidence.

Reads docs/capabilities.json and (optionally) a CI result file, then emits a
ROADMAP.md where every human checkbox is derived from declared evidence.

Usage:
    python scripts/roadmap_status.py
    python scripts/roadmap_status.py --ci-results ci-results.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES_PATH = ROOT / "docs" / "capabilities.json"
ROADMAP_PATH = ROOT / "docs" / "ROADMAP.md"


@dataclass(frozen=True)
class EvidenceResult:
    name: str
    passed: bool
    output: str
    duration_ms: float


@dataclass
class CapabilityStatus:
    capability: dict[str, Any]
    evidence_results: list[EvidenceResult]
    missing_artifacts: list[str]

    @property
    def passed(self) -> bool:
        if not self.evidence_results:
            return False
        return all(r.passed for r in self.evidence_results) and not self.missing_artifacts

    @property
    def status(self) -> str:
        return "verified" if self.passed else "unverified"


def load_capabilities() -> dict[str, Any]:
    with CAPABILITIES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(command: str, timeout: float = 120.0) -> EvidenceResult:
    import time

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        passed = proc.returncode == 0
        if passed:
            output = ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:]
        else:
            output = f"command failed with exit code {proc.returncode}"
    except subprocess.TimeoutExpired:
        passed = False
        output = "timeout"
    duration_ms = (time.perf_counter() - start) * 1000
    return EvidenceResult(
        name=command,
        passed=passed,
        output=output,
        duration_ms=duration_ms,
    )


def check_artifact(path: str) -> bool:
    return (ROOT / path).exists()


def evaluate_ci_job(job: str, ci_results: dict[str, Any] | None) -> EvidenceResult:
    jobs = ci_results.get("jobs", {}) if ci_results else {}
    result = jobs.get(job) if isinstance(jobs, dict) else None
    if result is None and ci_results:
        result = ci_results.get(job)
    if result is None:
        return EvidenceResult(
            name=job,
            passed=False,
            output=f"CI result unavailable for job: {job}",
            duration_ms=0.0,
        )

    if isinstance(result, dict):
        conclusion = result.get("conclusion", result.get("status", "unknown"))
    elif isinstance(result, bool):
        conclusion = "success" if result else "failure"
    else:
        conclusion = str(result)
    passed = str(conclusion).lower() in {"success", "passed"}
    return EvidenceResult(
        name=job,
        passed=passed,
        output=f"CI job {job}: {conclusion}",
        duration_ms=0.0,
    )


def evaluate_capability(
    cap: dict[str, Any],
    checks: dict[str, Any],
    ci_results: dict[str, Any] | None = None,
    evidence_cache: dict[str, EvidenceResult] | None = None,
    execute_commands: bool = True,
) -> CapabilityStatus:
    results: list[EvidenceResult] = []
    for ev in cap.get("evidence", []):
        if evidence_cache is not None and ev in evidence_cache:
            results.append(evidence_cache[ev])
            continue
        spec = checks.get(ev)
        if not spec:
            results.append(EvidenceResult(name=ev, passed=False, output="unknown evidence type", duration_ms=0.0))
        elif spec.get("type") == "command" and execute_commands:
            results.append(run_command(spec["command"], timeout=spec.get("timeout", 120.0)))
        elif spec.get("type") == "command":
            results.append(
                EvidenceResult(
                    name=spec["command"],
                    passed=False,
                    output="command evidence not executed",
                    duration_ms=0.0,
                )
            )
        elif spec.get("type") == "ci":
            job = spec.get("job", ev)
            ci_result = evaluate_ci_job(job, ci_results)
            results.append(
                EvidenceResult(
                    name=ev,
                    passed=ci_result.passed,
                    output=ci_result.output,
                    duration_ms=ci_result.duration_ms,
                )
            )
        elif spec.get("type") == "manual":
            results.append(
                EvidenceResult(
                    name=ev,
                    passed=False,
                    output="manual claims are not verifiable evidence",
                    duration_ms=0.0,
                )
            )
        else:
            results.append(EvidenceResult(name=ev, passed=False, output=f"unknown evidence type: {spec.get('type')}", duration_ms=0.0))
        if evidence_cache is not None:
            evidence_cache[ev] = results[-1]

    missing = [a for a in cap.get("artifacts", []) if not check_artifact(a)]
    return CapabilityStatus(capability=cap, evidence_results=results, missing_artifacts=missing)


def build_roadmap(capabilities: dict[str, Any], execute_commands: bool = True) -> str:
    lines: list[str] = [
        "# Roadmap",
        "",
        "This file is generated by `scripts/roadmap_status.py`. Do not edit manually.",
        "",
    ]

    stages = capabilities.get("stages", [])
    caps = capabilities.get("capabilities", [])
    checks = capabilities.get("evidence_checks", {})
    ci_results = capabilities.get("_ci_results")

    evidence_cache: dict[str, EvidenceResult] = {}
    statuses = [
        evaluate_capability(
            capability,
            checks,
            ci_results,
            evidence_cache,
            execute_commands=execute_commands,
        )
        for capability in caps
    ]
    by_stage: dict[str, list[CapabilityStatus]] = {}
    for s in statuses:
        by_stage.setdefault(s.capability.get("stage", "unknown"), []).append(s)

    for stage in stages:
        sid = stage["id"]
        sname = stage["name"]
        stage_caps = by_stage.get(sid, [])
        if not stage_caps:
            status = "unverified"
        elif all(c.passed for c in stage_caps):
            status = "verified"
        elif any(c.passed for c in stage_caps):
            status = "partially verified"
        else:
            status = "unverified"

        lines.append(f"## {sid} — {sname} [{status}]")
        lines.append("")
        for cs in stage_caps:
            cap = cs.capability
            marker = "x" if cs.passed else " "
            lines.append(f"- [{marker}] [{cap.get('id')}] {cap.get('name')} — {cs.status}")
            for er in cs.evidence_results:
                if not er.passed:
                    lines.append(f"    - {er.name}: {er.output[:120]}")
            if cs.missing_artifacts:
                lines.append(f"    - missing artifacts: {', '.join(cs.missing_artifacts)}")
        lines.append("")

    return "\n".join(lines)


def roadmap_diff(expected: str, roadmap_path: Path = ROADMAP_PATH) -> str | None:
    actual = roadmap_path.read_text(encoding="utf-8") if roadmap_path.exists() else ""
    if actual == expected:
        return None
    return "".join(
        unified_diff(
            actual.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=str(roadmap_path),
            tofile="generated ROADMAP.md",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate computed ROADMAP.md")
    parser.add_argument("--ci-results", type=Path, help="Path to a JSON file with CI results")
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")
    output_mode.add_argument("--check", action="store_true", help="Fail if committed ROADMAP.md differs from generated content")
    parser.add_argument(
        "--no-run-commands",
        action="store_true",
        help="Generate deterministically without executing command evidence",
    )
    args = parser.parse_args()

    capabilities = load_capabilities()
    if args.ci_results:
        with args.ci_results.open("r", encoding="utf-8") as f:
            capabilities["_ci_results"] = json.load(f)

    roadmap = build_roadmap(capabilities, execute_commands=not args.no_run_commands)
    if args.check:
        diff = roadmap_diff(roadmap)
        if diff is not None:
            print("ROADMAP CHECK FAILED", file=sys.stderr)
            print(diff, file=sys.stderr, end="")
            return 1
        print("ROADMAP CHECK PASSED")
    elif args.dry_run:
        print(roadmap)
    else:
        ROADMAP_PATH.write_text(roadmap, encoding="utf-8")
        print(f"Generated {ROADMAP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
