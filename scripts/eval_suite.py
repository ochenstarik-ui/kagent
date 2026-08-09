"""Replayable eval suite for KAgent.

Runs frozen repository snapshots through a deterministic agent task and records
metrics: autonomy rate, interventions, repair cycles, escape defects, cost,
time-to-first-artifact, and policy violations.

Usage:
    python scripts/eval_suite.py --list
    python scripts/eval_suite.py --replay --case feature_add_endpoint
    python scripts/eval_suite.py --gate
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
CASES_DIR = EVAL_DIR / "cases"
REPORTS_DIR = EVAL_DIR / "reports"
METRICS_SCHEMA_PATH = EVAL_DIR / "metrics_schema.json"


@dataclass
class EvalResult:
    case_id: str
    category: str
    passed: bool
    autonomy: bool
    interventions: int
    repair_cycles: int
    escape_defects: int
    time_to_first_artifact_ms: int
    integrated_change_cost_usd: float
    policy_violation_attempts: int
    duration_ms: int
    errors: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    timestamp: str
    autonomy_rate: float
    rework_rate: float
    average_repair_cycles: float
    escape_defects_total: int
    average_time_to_first_artifact_ms: float
    average_cost_usd: float
    policy_violation_attempts_total: int
    results: list[dict[str, Any]]
    gate_passed: bool


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_cases() -> list[Path]:
    if not CASES_DIR.exists():
        return []
    return sorted(d for d in CASES_DIR.iterdir() if d.is_dir())


def validate_draft_case(case_dir: Path, contract: dict[str, Any]) -> None:
    runnable_fields = [
        field_name
        for field_name in ("replay_script", "first_artifact", "acceptance")
        if contract.get(field_name)
    ]
    base = case_dir / "base.tar.gz"
    if base.exists() and tarfile.is_tarfile(base):
        runnable_fields.append("base.tar.gz")
    if runnable_fields:
        fields = ", ".join(runnable_fields)
        raise ValueError(f"draft case {case_dir.name} appears runnable: {fields}")


def list_runnable_cases() -> list[Path]:
    runnable: list[Path] = []
    for case_dir in list_cases():
        contract = load_json(case_dir / "contract.json")
        if contract.get("status", "active") == "draft":
            validate_draft_case(case_dir, contract)
            continue
        runnable.append(case_dir)
    return runnable


def run_shell(cmd: list[str], cwd: Path, timeout: float = 120.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def materialize_case(case_dir: Path) -> Path:
    base = case_dir / "base.tar.gz"
    workdir = Path(tempfile.mkdtemp(prefix=f"kagent-eval-{case_dir.name}-"))
    if base.exists():
        try:
            with tarfile.open(base, "r:gz") as tar:
                tar.extractall(workdir)
        except (tarfile.ReadError, OSError):
            # Invalid or placeholder archive; replay mode creates files via script.
            pass
    return workdir


def run_agent_task(contract: dict[str, Any], workdir: Path) -> EvalResult:
    """Simulated agent task for replay mode.

    In replay mode, the suite does not call external model providers. Instead it
    applies a deterministic script (if present) and checks acceptance criteria.
    """
    start = time.perf_counter()
    t0_artifact = start
    repair_cycles = 0
    errors: list[str] = []
    artifacts: list[str] = []

    replay_script = contract.get("replay_script")
    if replay_script:
        code, out, err = run_shell(["bash", "-c", replay_script], workdir)
        if code != 0:
            errors.append(f"replay script failed: {err or out}")
        else:
            first_artifact = contract.get("first_artifact")
            if first_artifact and (workdir / first_artifact).exists():
                t0_artifact = time.perf_counter()
                artifacts.append(first_artifact)

    # Check acceptance criteria
    acceptance = contract.get("acceptance", [])
    passed = True
    for check in acceptance:
        kind = check.get("kind")
        if kind == "file_exists":
            if not (workdir / check["path"]).exists():
                passed = False
                errors.append(f"missing file: {check['path']}")
        elif kind == "file_contains":
            path = workdir / check["path"]
            if not path.exists():
                passed = False
                errors.append(f"missing file: {check['path']}")
            elif check["text"] not in path.read_text(encoding="utf-8"):
                passed = False
                errors.append(f"file does not contain expected text: {check['path']}")
        elif kind == "command":
            # Support commands that contain spaces and quoted strings by passing through bash.
            code, out, err = run_shell(["bash", "-c", check["command"]], workdir)
            if code != 0:
                passed = False
                errors.append(f"acceptance command failed: {check['command']}: {err or out}")
        elif kind == "no_file_contains":
            path = workdir / check["path"]
            if path.exists() and check["text"] in path.read_text(encoding="utf-8"):
                passed = False
                errors.append(f"file contains forbidden text: {check['path']}")
        else:
            passed = False
            errors.append(f"unknown acceptance kind: {kind}")

    duration_ms = int((time.perf_counter() - start) * 1000)
    ttfa_ms = int((t0_artifact - start) * 1000)

    return EvalResult(
        case_id=contract["id"],
        category=contract.get("category", "feature"),
        passed=passed,
        autonomy=True,
        interventions=0,
        repair_cycles=repair_cycles,
        escape_defects=0,
        time_to_first_artifact_ms=ttfa_ms,
        integrated_change_cost_usd=0.0,
        policy_violation_attempts=0,
        duration_ms=duration_ms,
        errors=errors,
        artifacts=artifacts,
    )


def run_case(case_dir: Path) -> EvalResult:
    contract = load_json(case_dir / "contract.json")
    if contract.get("status", "active") == "draft":
        validate_draft_case(case_dir, contract)
        raise ValueError(f"draft case {case_dir.name} cannot be replayed")
    workdir = materialize_case(case_dir)
    try:
        result = run_agent_task(contract, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return result


def run_all() -> EvalReport:
    cases = list_runnable_cases()
    results: list[EvalResult] = []
    for case_dir in cases:
        result = run_case(case_dir)
        results.append(result)

    if not results:
        return EvalReport(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            autonomy_rate=0.0,
            rework_rate=0.0,
            average_repair_cycles=0.0,
            escape_defects_total=0,
            average_time_to_first_artifact_ms=0.0,
            average_cost_usd=0.0,
            policy_violation_attempts_total=0,
            results=[],
            gate_passed=False,
        )

    passed = [r for r in results if r.passed]
    autonomy_rate = len(passed) / len(results)
    rework_rate = 0.0  # replay mode: no rework
    avg_repair = sum(r.repair_cycles for r in results) / len(results)
    total_escapes = sum(r.escape_defects for r in results)
    avg_ttfa = sum(r.time_to_first_artifact_ms for r in results) / len(results)
    avg_cost = sum(r.integrated_change_cost_usd for r in results) / len(results)
    total_policy = sum(r.policy_violation_attempts for r in results)

    # Gate: all cases pass and no escape defects
    gate_passed = len(passed) == len(results) and total_escapes == 0

    return EvalReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        autonomy_rate=autonomy_rate,
        rework_rate=rework_rate,
        average_repair_cycles=avg_repair,
        escape_defects_total=total_escapes,
        average_time_to_first_artifact_ms=avg_ttfa,
        average_cost_usd=avg_cost,
        policy_violation_attempts_total=total_policy,
        results=[asdict(r) for r in results],
        gate_passed=gate_passed,
    )


def print_report(report: EvalReport) -> None:
    print(json.dumps(asdict(report), indent=2))


def load_baseline() -> dict[str, Any]:
    baseline_path = EVAL_DIR / "baseline.json"
    if baseline_path.exists():
        return load_json(baseline_path)
    return {}


def check_regressions(report: EvalReport) -> list[str]:
    baseline = load_baseline()
    errors: list[str] = []
    if "autonomy_rate" in baseline and report.autonomy_rate < baseline["autonomy_rate"]:
        errors.append(f"autonomy rate regressed: {report.autonomy_rate} < {baseline['autonomy_rate']}")
    if "escape_defects_total" in baseline and report.escape_defects_total > baseline["escape_defects_total"]:
        errors.append(f"escape defects regressed: {report.escape_defects_total} > {baseline['escape_defects_total']}")
    if not report.gate_passed:
        errors.append("eval gate failed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="KAgent eval suite")
    parser.add_argument("--list", action="store_true", help="List available cases")
    parser.add_argument("--replay", action="store_true", help="Run all cases in replay mode")
    parser.add_argument("--case", type=str, help="Run a specific case")
    parser.add_argument("--gate", action="store_true", help="Fail if gate is not met")
    args = parser.parse_args()

    if args.list:
        for case_dir in list_cases():
            print(case_dir.name)
        return 0

    if args.case:
        case_dir = CASES_DIR / args.case
        if not case_dir.exists():
            print(f"case not found: {args.case}", file=sys.stderr)
            return 1
        report = EvalReport(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            autonomy_rate=0.0,
            rework_rate=0.0,
            average_repair_cycles=0.0,
            escape_defects_total=0,
            average_time_to_first_artifact_ms=0.0,
            average_cost_usd=0.0,
            policy_violation_attempts_total=0,
            results=[asdict(run_case(case_dir))],
            gate_passed=False,
        )
    else:
        report = run_all()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    save_json(REPORTS_DIR / "latest.json", asdict(report))
    print_report(report)

    if args.gate:
        errors = check_regressions(report)
        if errors:
            print("GATE FAILED", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print("GATE PASSED")

    return 0


if __name__ == "__main__":
    sys.exit(main())
