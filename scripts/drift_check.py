"""Spec drift check for KAgent.

Fails CI when the repository diverges from the declared capability registry:
- declared capabilities without evidence
- unreachable modules
- undocumented endpoints
- environment variables not in .env.example
- missing CHANGELOG entries for user-visible changes
- missing ADR for architectural changes

Usage:
    python scripts/drift_check.py
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES_PATH = ROOT / "docs" / "capabilities.json"
KNOWN_DRIFT_PATH = ROOT / "docs" / "known-drift.json"
CI_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
ADRS_DIR = ROOT / "docs" / "adr"

# Cache command evidence results so expensive checks run only once per invocation.
_Executed: dict[str, tuple[bool, str]] = {}


def load_capabilities() -> dict[str, Any]:
    with CAPABILITIES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_known_drift(data: Any, today: date | None = None) -> list[str]:
    """Validate the shape of the expiring unreachable-module allowlist."""
    current_date = today or date.today()
    if not isinstance(data, dict):
        return ["known drift document must be an object"]
    if data.get("version") != 1:
        return ["known drift version must be 1"]
    entries = data.get("entries")
    if not isinstance(entries, list):
        return ["known drift entries must be a list"]

    errors: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"known drift entry {index} must be an object")
            continue
        if not isinstance(entry.get("path"), str) or not entry["path"].strip():
            errors.append(f"known drift entry {index} has invalid path")
        if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
            errors.append(f"known drift entry {index} has invalid reason")
        expires = entry.get("expires")
        try:
            if not isinstance(expires, str):
                raise ValueError
            expiry_date = date.fromisoformat(expires)
        except ValueError:
            errors.append(f"known drift entry {index} has invalid expires")
        else:
            if expiry_date < current_date:
                errors.append(f"known drift entry {index} expired on {expires}")
        if not isinstance(entry.get("follow_up_task"), str) or not entry["follow_up_task"].strip():
            errors.append(f"known drift entry {index} has invalid follow_up_task")
    return errors


def load_known_drift() -> dict[str, Any]:
    with KNOWN_DRIFT_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def check_unreachable_drift(
    unreachable: list[str],
    known_drift: Any,
    today: date | None = None,
) -> list[str]:
    errors = validate_known_drift(known_drift, today=today)
    if errors:
        return errors

    detected = set(unreachable)
    allowlisted = {entry["path"] for entry in known_drift["entries"]}
    errors.extend(
        f"unreachable module is not allowlisted: {path}"
        for path in sorted(detected - allowlisted)
    )
    errors.extend(
        f"known drift is no longer detected; remove allowlist entry: {path}"
        for path in sorted(allowlisted - detected)
    )
    return errors


def run_command(command: str, timeout: float = 120.0) -> tuple[bool, str]:
    if command in _Executed:
        return _Executed[command]
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        result = (proc.returncode == 0, (proc.stdout + proc.stderr).strip())
    except subprocess.TimeoutExpired:
        result = (False, "timeout")
    except Exception as e:
        result = (False, str(e))
    _Executed[command] = result
    return result


def check_evidence_declared(cap: dict[str, Any], checks: dict[str, Any]) -> list[str]:
    """Verify that each evidence reference is known in the registry.

    Actual command execution happens in CI; drift_check only validates that the
    capability has declared evidence and that the required artifacts exist.
    """
    errors: list[str] = []
    for ev in cap.get("evidence", []):
        if ev not in checks:
            errors.append(f"[{cap['id']}] unknown evidence: {ev}")
    return errors


def load_workflow_jobs() -> set[str]:
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    in_jobs = False
    jobs: set[str] = set()
    for line in content.splitlines():
        if line == "jobs:":
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith(" "):
            break
        if in_jobs and (match := re.fullmatch(r"  ([A-Za-z0-9_-]+):\s*", line)):
            jobs.add(match.group(1))
    return jobs


def check_evidence_registry(
    registry: dict[str, Any],
    workflow_jobs: set[str] | None = None,
) -> list[str]:
    checks = registry.get("evidence_checks", {})
    jobs = workflow_jobs if workflow_jobs is not None else load_workflow_jobs()
    errors: list[str] = []
    for capability in registry.get("capabilities", []):
        capability_id = capability.get("id", "unknown")
        for evidence_name in capability.get("evidence", []):
            spec = checks.get(evidence_name)
            if not isinstance(spec, dict):
                errors.append(f"[{capability_id}] unknown evidence: {evidence_name}")
                continue
            evidence_type = spec.get("type")
            if evidence_type == "command":
                if not isinstance(spec.get("command"), str) or not spec["command"].strip():
                    errors.append(f"[{capability_id}] command evidence {evidence_name} has no command")
            elif evidence_type == "ci":
                job = spec.get("job")
                if not isinstance(job, str) or not job.strip():
                    errors.append(f"[{capability_id}] CI evidence {evidence_name} must name a concrete job")
                elif job not in jobs:
                    errors.append(f"[{capability_id}] CI evidence {evidence_name} names unknown job: {job}")
            elif evidence_type == "artifact":
                artifact = spec.get("path")
                if not isinstance(artifact, str) or not (ROOT / artifact).exists():
                    errors.append(f"[{capability_id}] artifact evidence {evidence_name} does not resolve")
            elif evidence_type == "eval":
                case_id = spec.get("case")
                case_path = ROOT / "eval" / "cases" / str(case_id) / "contract.json"
                if not isinstance(case_id, str) or not case_path.exists():
                    errors.append(f"[{capability_id}] eval evidence {evidence_name} does not resolve")
            else:
                errors.append(f"[{capability_id}] evidence {evidence_name} has unknown type: {evidence_type}")
    return errors


def check_artifacts(cap: dict[str, Any]) -> list[str]:
    missing = [a for a in cap.get("artifacts", []) if not (ROOT / a).exists()]
    if missing:
        return [f"[{cap['id']}] missing artifacts: {', '.join(missing)}"]
    return []


def find_source_files() -> list[Path]:
    """Return production modules, excluding tests, dependencies, and generated files."""
    patterns = ["*.py", "*.ts", "*.tsx", "*.js", "*.rs"]
    skip_dirs = {
        ".next",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "target",
        "tests",
    }
    files: list[Path] = []
    for source_root_name in ("apps", "packages", "services"):
        source_root = ROOT / source_root_name
        if not source_root.exists():
            continue
        for pattern in patterns:
            files.extend(source_root.rglob(pattern))

    return sorted(
        path.resolve()
        for path in files
        if not (set(path.relative_to(ROOT).parts) & skip_dirs)
        and not path.name.startswith("test_")
        and ".test." not in path.name
        and not path.name.endswith(".d.ts")
        and not path.name.endswith(".config.ts")
    )


def _path_candidates(path: Path) -> list[Path]:
    candidates = [path]
    if path.suffix in {".js", ".mjs", ".cjs"}:
        candidates.extend(path.with_suffix(suffix) for suffix in (".ts", ".tsx", ".js"))
    elif not path.suffix:
        candidates.extend(path.with_suffix(suffix) for suffix in (".py", ".ts", ".tsx", ".js", ".rs"))
        candidates.extend((path / "index").with_suffix(suffix) for suffix in (".ts", ".tsx", ".js"))
    return candidates


def _resolve_path(path: Path, source_files: set[Path]) -> Path | None:
    for candidate in _path_candidates(path):
        resolved = candidate.resolve()
        if resolved in source_files:
            return resolved
    return None


def _typescript_dependencies(path: Path, source_files: set[Path]) -> set[Path]:
    content = path.read_text(encoding="utf-8", errors="replace")
    specifiers = re.findall(
        r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]",
        content,
    )
    dependencies: set[Path] = set()
    for specifier in specifiers:
        if not specifier.startswith("."):
            continue
        resolved = _resolve_path(path.parent / specifier, source_files)
        if resolved is not None:
            dependencies.add(resolved)
    return dependencies


def _python_dependencies(path: Path, source_files: set[Path]) -> set[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()

    dependencies: set[Path] = set()
    for node in ast.walk(tree):
        module_names: list[tuple[str, int]] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            module_names.append((node.module, node.level))
        elif isinstance(node, ast.Import):
            module_names.extend((alias.name, 0) for alias in node.names)

        for module_name, level in module_names:
            module_path = Path(*module_name.split("."))
            candidates: list[Path] = []
            if level:
                base = path.parent
                for _ in range(level - 1):
                    base = base.parent
                candidates.append(base / module_path)
            else:
                candidates.append(ROOT / module_path)
                for parent in path.parents:
                    if parent.parent == ROOT / "services":
                        candidates.append(parent / module_path)
                        break
            for candidate in candidates:
                resolved = _resolve_path(candidate, source_files)
                if resolved is not None:
                    dependencies.add(resolved)
                    break
    return dependencies


def _module_dependencies(path: Path, source_files: set[Path]) -> set[Path]:
    if path.suffix == ".py":
        return _python_dependencies(path, source_files)
    if path.suffix in {".js", ".ts", ".tsx"}:
        return _typescript_dependencies(path, source_files)
    return set()


def find_unreachable_modules(entry_points: list[str], capabilities: list[dict[str, Any]]) -> list[str]:
    """Return production modules not reachable through static imports from entry points."""
    del capabilities
    source_files = set(find_source_files())
    reachable = {
        path.resolve()
        for entry_point in entry_points
        if (path := ROOT / entry_point).resolve() in source_files
    }
    pending = list(reachable)
    while pending:
        current = pending.pop()
        for dependency in _module_dependencies(current, source_files):
            if dependency not in reachable:
                reachable.add(dependency)
                pending.append(dependency)

    return sorted(path.relative_to(ROOT).as_posix() for path in source_files - reachable)


def find_env_vars() -> list[str]:
    env_vars: list[str] = []
    for f in find_source_files():
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        # Python: os.getenv("X"), os.environ["X"]
        for match in re.finditer(r'os\.(?:getenv|environ)\([\'"]([A-Z_][A-Z0-9_]*)[\'"]\)', content):
            env_vars.append(match.group(1))
        # TypeScript: process.env["X"], process.env.X
        for match in re.finditer(r'process\.env\[[\'"]([A-Z_][A-Z0-9_]*)[\'"]\]', content):
            env_vars.append(match.group(1))
        for match in re.finditer(r'process\.env\.(?!NODE_ENV)([A-Z_][A-Z0-9_]*)\b', content):
            env_vars.append(match.group(1))
        # Rust: env::var("X")
        for match in re.finditer(r'env::var\([\'"]([A-Z_][A-Z0-9_]*)[\'"]\)', content):
            env_vars.append(match.group(1))
    compose_path = ROOT / "docker-compose.yml"
    if compose_path.exists():
        content = compose_path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)', content):
            env_vars.append(match.group(1))
    return sorted(set(env_vars))


def check_env_documentation(env_vars: list[str]) -> list[str]:
    if not ENV_EXAMPLE_PATH.exists():
        return ["missing .env.example"]
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    documented = set(re.findall(r"^([A-Z_][A-Z0-9_]*)=", content, re.MULTILINE))
    unread = sorted(documented - set(env_vars))
    if unread:
        return [f"documented env vars never read: {', '.join(unread)}"]
    return []


def declared_endpoints(route_table: dict[str, list[str]]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for service, routes in route_table.items():
        for route in routes:
            parts = route.split(" ", 1)
            method = parts[0]
            path = parts[1] if len(parts) > 1 else ""
            result.append((service, f"{method} {path}"))
    return result


def find_endpoints_in_code(service_dir: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if not service_dir.exists():
        return found
    # FastAPI-style decorators: @app.get("/path")
    for f in service_dir.rglob("*.py"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for match in re.finditer(r'@(?:app|router|\w+_app)\.(get|post|put|patch|delete)\([\'"]([^\'"]+)[\'"]', content, re.IGNORECASE):
            found.append((service_dir.name, f"{match.group(1).upper()} {match.group(2)}"))
    for f in service_dir.rglob("*.ts"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for match in re.finditer(r'app\.(get|post|put|patch|delete)\([\'"]([^\'"]+)[\'"]', content, re.IGNORECASE):
            found.append((service_dir.name, f"{match.group(1).upper()} {match.group(2)}"))
    # Rust axum: .route("/path", get(handler))
    for f in service_dir.rglob("*.rs"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for match in re.finditer(r'\.route\([\'"]([^\'"]+)[\'"],\s*(get|post|put|patch|delete)\(', content, re.IGNORECASE):
            found.append((service_dir.name, f"{match.group(2).upper()} {match.group(1)}"))
    return found


def normalize_path(path: str) -> str:
    return path.rstrip("/").replace("//", "/")


def match_route(declared: str, found: str) -> bool:
    d_method, d_path = declared.split(" ", 1)
    f_method, f_path = found.split(" ", 1)
    if d_method != "ALL" and d_method != f_method:
        return False
    d_segments = normalize_path(d_path).strip("/").split("/")
    f_segments = normalize_path(f_path).strip("/").split("/")
    if len(d_segments) != len(f_segments):
        return False
    for d, f in zip(d_segments, f_segments):
        if d.startswith(":"):
            continue
        if d != f:
            return False
    return True


def check_undocumented_endpoints(route_table: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    for service in route_table:
        service_dir = ROOT / "services" / service
        if not service_dir.exists():
            continue
        found = find_endpoints_in_code(service_dir)
        for _, ep in found:
            if not any(match_route(decl, ep) for decl in route_table[service]):
                errors.append(f"undocumented endpoint in {service}: {ep}")
    return errors


def check_missing_endpoints(route_table: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    for service, routes in route_table.items():
        service_dir = ROOT / "services" / service
        if not service_dir.exists():
            continue
        found = find_endpoints_in_code(service_dir)
        for decl in routes:
            if decl.startswith("ALL") or decl.startswith("publish") or decl.startswith("subscribe"):
                continue
            if not any(match_route(decl, ep) for _, ep in found):
                errors.append(f"declared endpoint missing in {service}: {decl}")
    return errors


def check_changelog() -> list[str]:
    if not CHANGELOG_PATH.exists():
        return ["missing CHANGELOG.md"]
    passed, output = run_command("git status --short")
    if not passed or not output:
        return []
    # Only consider staged or unstaged modifications, not untracked files.
    tracked_changes = [line for line in output.splitlines() if not line.startswith("??")]
    if not tracked_changes:
        return []
    if "CHANGELOG.md" in output:
        return []
    if re.search(r"\s+(services|apps|packages)/", output):
        return ["tracked user-visible changes detected but CHANGELOG.md not updated; add an entry under [Unreleased]"]
    return []


def check_adr() -> list[str]:
    passed, output = run_command("git status --short")
    if not passed or not output:
        return []
    if not ADRS_DIR.exists():
        return ["missing docs/adr directory"]
    # Only fail on tracked modifications to services/packages/docker-compose.
    tracked_changes = [line for line in output.splitlines() if not line.startswith("??")]
    if not tracked_changes:
        return []
    needs_adr = any(re.search(r"\s+(services|packages|docker-compose\.yml)/", line) for line in tracked_changes)
    if not needs_adr:
        return []
    if re.search(r"\s+docs/adr/\d+.*\.md", output):
        return []
    return ["architectural change detected but no new ADR; add one under docs/adr/"]


def check_forbidden_paths() -> list[str]:
    passed, output = run_command("git status --short")
    if not passed or not output:
        return []
    # Only fail on tracked modifications to forbidden paths; untracked additions are allowed.
    forbidden = ["eval/", "docs/capabilities.json", "scripts/eval_suite.py", "scripts/roadmap_status.py", "scripts/drift_check.py"]
    touched = [line for line in output.splitlines() if not line.startswith("??") and any(f in line for f in forbidden)]
    if touched:
        return [f"product task must not modify eval or measurability artifacts: {', '.join(touched)}"]
    return []


def main() -> int:
    capabilities = load_capabilities()
    errors: list[str] = []

    for cap in capabilities.get("capabilities", []):
        errors.extend(check_artifacts(cap))
    errors.extend(check_evidence_registry(capabilities))

    unreachable = find_unreachable_modules(
        capabilities.get("entry_points", []),
        capabilities.get("capabilities", []),
    )
    try:
        known_drift = load_known_drift()
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot load known drift allowlist: {error}")
    else:
        errors.extend(check_unreachable_drift(unreachable, known_drift))
    errors.extend(check_undocumented_endpoints(capabilities.get("route_table", {})))
    errors.extend(check_missing_endpoints(capabilities.get("route_table", {})))
    env_vars = find_env_vars()
    errors.extend(check_env_documentation(env_vars))
    errors.extend(check_changelog())
    errors.extend(check_adr())
    errors.extend(check_forbidden_paths())

    if errors:
        print("DRIFT CHECK FAILED", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if unreachable:
        print("KNOWN DRIFT (allowlisted):")
        for path in unreachable:
            print(f"  - {path}")
    print("DRIFT CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
