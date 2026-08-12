"""Deterministic, provider-free replay runner for KAgent evaluation cases."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
CASES_DIR = EVAL_DIR / "cases"
REPORTS_DIR = EVAL_DIR / "reports"
METRICS_SCHEMA_PATH = EVAL_DIR / "metrics_schema.json"
_MAX_SNAPSHOT_BYTES = 1_000_000
_SUBPROCESS_ENV_ALLOWLIST = {
    "COMSPEC",
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
}


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
    empty_diff_rejected: bool
    replay_acceptance_passed: bool
    mutation_rejected: bool
    provider_calls: int = 0
    tokens_spent: int = 0
    provider_environment_scrubbed: bool = True
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
    provider_calls_total: int
    tokens_spent_total: int
    results: list[dict[str, Any]]
    gate_passed: bool


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def list_cases() -> list[Path]:
    if not CASES_DIR.exists():
        return []
    return sorted(path for path in CASES_DIR.iterdir() if path.is_dir())


def validate_draft_case(case_dir: Path, contract: dict[str, Any]) -> None:
    runnable_fields = [
        name
        for name in ("replay_script", "cassette", "verifier", "mutation", "acceptance")
        if contract.get(name)
    ]
    base = case_dir / contract.get("snapshot", "base.tar.gz")
    if base.exists() and tarfile.is_tarfile(base):
        runnable_fields.append(base.name)
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


def scrub_provider_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in _SUBPROCESS_ENV_ALLOWLIST
    }
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def run_shell(cmd: list[str], cwd: Path, timeout: float = 120.0) -> tuple[int, str, str]:
    try:
        process = subprocess.run(
            cmd,
            cwd=cwd,
            env=scrub_provider_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return process.returncode, process.stdout, process.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        return -1, "", str(error)


def _safe_relative_path(value: str) -> Path:
    posix = PurePosixPath(value)
    if (
        posix.is_absolute()
        or ".." in posix.parts
        or not posix.parts
        or "\\" in value
        or any(":" in part for part in posix.parts)
    ):
        raise ValueError(f"unsafe relative path: {value}")
    return Path(*posix.parts)


def materialize_case(case_dir: Path, snapshot_name: str = "base.tar.gz") -> Path:
    snapshot = case_dir / snapshot_name
    if not snapshot.is_file() or not tarfile.is_tarfile(snapshot):
        raise ValueError(f"case {case_dir.name} has no valid snapshot: {snapshot_name}")
    workdir = Path(tempfile.mkdtemp(prefix=f"kagent-eval-{case_dir.name}-"))
    total_size = 0
    try:
        with tarfile.open(snapshot, "r:gz") as archive:
            for member in archive.getmembers():
                relative = _safe_relative_path(member.name)
                if not (member.isdir() or member.isfile()):
                    raise ValueError(f"unsupported archive member: {member.name}")
                total_size += member.size
                if total_size > _MAX_SNAPSHOT_BYTES:
                    raise ValueError("snapshot exceeds extraction limit")
                destination = workdir / relative
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(f"cannot read archive member: {member.name}")
                with source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    return workdir


def apply_operations(workdir: Path, operations: list[dict[str, Any]]) -> list[str]:
    artifacts: list[str] = []
    for operation in operations:
        if operation.get("kind") != "write":
            raise ValueError(f"unsupported replay operation: {operation.get('kind')}")
        relative = _safe_relative_path(operation["path"])
        destination = workdir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(operation["content"], encoding="utf-8", newline="\n")
        artifacts.append(relative.as_posix())
    return artifacts


def measure_acceptance(
    case_dir: Path, contract: dict[str, Any], workdir: Path
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for command in contract.get("acceptance", []):
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            raise ValueError("acceptance commands must be argument arrays")
        code, output, error = run_shell(command, workdir)
        if code != 0:
            detail = (error or output).strip()
            errors.append(f"acceptance command failed ({code}): {command!r}: {detail}")
    verifier = case_dir / contract["verifier"]
    code, output, error = run_shell(
        [sys.executable, "-I", str(verifier), str(workdir)], workdir
    )
    if code != 0:
        detail = (error or output).strip()
        errors.append(f"hidden verifier failed ({code}): {detail}")
    return not errors, errors


def run_agent_task(case_dir: Path, contract: dict[str, Any], workdir: Path) -> EvalResult:
    start = time.perf_counter()
    base_passed, _ = measure_acceptance(case_dir, contract, workdir)
    cassette = load_json(case_dir / contract["cassette"])
    metrics = cassette["metrics"]
    artifacts = apply_operations(workdir, cassette["response"]["operations"])
    artifact_time = time.perf_counter()
    replay_passed, replay_errors = measure_acceptance(case_dir, contract, workdir)
    expected = contract["expected_artifacts"]
    missing = [path for path in expected if not (workdir / _safe_relative_path(path)).is_file()]

    mutation_dir = Path(tempfile.mkdtemp(prefix=f"kagent-eval-mutation-{contract['id']}-"))
    try:
        shutil.copytree(workdir, mutation_dir, dirs_exist_ok=True)
        mutation = load_json(case_dir / contract["mutation"])
        apply_operations(mutation_dir, mutation["operations"])
        mutation_passed, _ = measure_acceptance(case_dir, contract, mutation_dir)
    finally:
        shutil.rmtree(mutation_dir, ignore_errors=True)

    empty_diff_rejected = not base_passed
    mutation_rejected = not mutation_passed
    errors = list(replay_errors)
    if not empty_diff_rejected:
        errors.append("untouched snapshot unexpectedly passed acceptance")
    if missing:
        errors.append(f"missing expected artifacts: {', '.join(missing)}")
    if not mutation_rejected:
        errors.append("declared adjacent-breaking mutation unexpectedly passed acceptance")
    passed = empty_diff_rejected and replay_passed and not missing and mutation_rejected
    duration_ms = int((time.perf_counter() - start) * 1000)
    return EvalResult(
        case_id=contract["id"],
        category=contract["category"],
        passed=passed,
        autonomy=passed,
        interventions=0,
        repair_cycles=int(metrics["repair_cycles"]),
        escape_defects=0,
        time_to_first_artifact_ms=int((artifact_time - start) * 1000),
        integrated_change_cost_usd=float(metrics["cost_usd"]),
        policy_violation_attempts=0,
        duration_ms=duration_ms,
        empty_diff_rejected=empty_diff_rejected,
        replay_acceptance_passed=replay_passed,
        mutation_rejected=mutation_rejected,
        errors=errors,
        artifacts=artifacts,
    )


def run_case(case_dir: Path) -> EvalResult:
    contract = load_json(case_dir / "contract.json")
    if contract.get("status", "active") == "draft":
        validate_draft_case(case_dir, contract)
        raise ValueError(f"draft case {case_dir.name} cannot be replayed")
    workdir = materialize_case(case_dir, contract.get("snapshot", "base.tar.gz"))
    try:
        return run_agent_task(case_dir, contract, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def build_report(results: list[EvalResult]) -> EvalReport:
    count = len(results)
    passed = sum(result.passed for result in results)
    return EvalReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        autonomy_rate=passed / count if count else 0.0,
        rework_rate=0.0,
        average_repair_cycles=(sum(result.repair_cycles for result in results) / count if count else 0.0),
        escape_defects_total=sum(result.escape_defects for result in results),
        average_time_to_first_artifact_ms=(
            sum(result.time_to_first_artifact_ms for result in results) / count if count else 0.0
        ),
        average_cost_usd=(
            sum(result.integrated_change_cost_usd for result in results) / count if count else 0.0
        ),
        policy_violation_attempts_total=sum(result.policy_violation_attempts for result in results),
        provider_calls_total=sum(result.provider_calls for result in results),
        tokens_spent_total=sum(result.tokens_spent for result in results),
        results=[asdict(result) for result in results],
        gate_passed=False,
    )


def run_all() -> EvalReport:
    return build_report([run_case(case_dir) for case_dir in list_runnable_cases()])


def print_report(report: EvalReport) -> None:
    print(json.dumps(asdict(report), indent=2))


def load_baseline() -> dict[str, Any]:
    baseline_path = EVAL_DIR / "baseline.json"
    return load_json(baseline_path) if baseline_path.exists() else {}


def check_regressions(report: EvalReport) -> list[str]:
    baseline = load_baseline()
    errors: list[str] = []
    if "autonomy_rate" in baseline and report.autonomy_rate < baseline["autonomy_rate"]:
        errors.append(f"autonomy rate regressed: {report.autonomy_rate} < {baseline['autonomy_rate']}")
    if "escape_defects_total" in baseline and report.escape_defects_total > baseline["escape_defects_total"]:
        errors.append(
            f"escape defects regressed: {report.escape_defects_total} > {baseline['escape_defects_total']}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="KAgent eval suite")
    parser.add_argument("--list", action="store_true", help="List available cases")
    parser.add_argument("--replay", action="store_true", help="Run cases from tracked cassettes")
    parser.add_argument("--case", help="Run a specific case")
    parser.add_argument("--gate", action="store_true", help="Report regressions without release gating")
    args = parser.parse_args()
    if args.list:
        for case_dir in list_cases():
            print(case_dir.name)
        return 0
    results = [run_case(CASES_DIR / args.case)] if args.case else [
        run_case(case_dir) for case_dir in list_runnable_cases()
    ]
    report = build_report(results)
    save_json(REPORTS_DIR / "latest.json", asdict(report))
    print_report(report)
    if args.gate:
        errors = check_regressions(report)
        for error in errors:
            print(f"REGRESSION: {error}", file=sys.stderr)
        return 1 if errors else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
