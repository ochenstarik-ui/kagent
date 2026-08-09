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

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES_PATH = ROOT / "docs" / "capabilities.json"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
ADRS_DIR = ROOT / "docs" / "adr"

# Cache command evidence results so expensive checks run only once per invocation.
_Executed: dict[str, tuple[bool, str]] = {}


def load_capabilities() -> dict[str, Any]:
    with CAPABILITIES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def check_artifacts(cap: dict[str, Any]) -> list[str]:
    missing = [a for a in cap.get("artifacts", []) if not (ROOT / a).exists()]
    if missing:
        return [f"[{cap['id']}] missing artifacts: {', '.join(missing)}"]
    return []


def find_source_files() -> list[Path]:
    patterns = ["*.py", "*.ts", "*.js", "*.rs"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(ROOT.rglob(pattern))
    # Exclude generated/dependency directories and well-known generated files.
    skip_names = {"node_modules", "target", "__pycache__", ".next", "dist", "build"}
    skip_files = {"next-env.d.ts"}
    return [
        f for f in files
        if not (set(f.parts) & skip_names) and f.name not in skip_files
    ]


def find_unreachable_modules(entry_points: list[str], capabilities: list[dict[str, Any]]) -> list[str]:
    """Return source files that are not reachable from any entry point.

    Reachability is determined by static import/require references. Declared
    capabilities are *not* automatically considered reachable — they must be
    imported by an entry point or test.
    """
    reachable: set[Path] = set()
    for ep in entry_points:
        path = ROOT / ep
        if path.exists():
            reachable.add(path)

    source_files = find_source_files()
    reachable_contents: dict[Path, str] = {}
    for f in reachable:
        try:
            reachable_contents[f] = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Iteratively expand reachable set by following imports.
    changed = True
    while changed:
        changed = False
        for f in source_files:
            if f in reachable:
                continue
            if _is_imported_by_reachable(f, reachable, reachable_contents):
                reachable.add(f)
                try:
                    reachable_contents[f] = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
                changed = True

    return sorted(
        str(f.relative_to(ROOT)) for f in source_files if f not in reachable
    )


def _is_imported_by_reachable(target: Path, reachable: set[Path], contents: dict[Path, str]) -> bool:
    target_rel = target.relative_to(ROOT)
    target_stem = target.stem
    target_rel_dot = str(target_rel.with_suffix("")).replace("\\", "/").replace("/", ".")
    target_rel_slash = str(target_rel.with_suffix("")).replace("\\", "/")

    for ep in reachable:
        content = contents.get(ep, "")
        if not content:
            continue
        # TypeScript / ESM relative imports: ./foo, ../bar/foo, ./foo.js
        if re.search(rf"(?:import\s+.*\s+from\s+|from\s+|require\s*\(\s*)['\"][^'\"]*{re.escape(target_rel_slash)}(?:\.\w+)?['\"]", content):
            return True
        # Python imports: from services.auth.src import totp, import totp
        if target_stem and re.search(rf"(?:from\s+{re.escape(target_rel_dot)}\s+import|import\s+{re.escape(target_rel_dot)}\b|from\s+\S*\s+import\s+.*\b{re.escape(target_stem)}\b)", content):
            return True
        # Direct import by stem for relative Python imports
        if target_stem and re.search(rf"\b{re.escape(target_stem)}\b", content):
            if re.search(rf"(?:from\s+\S*\s+import\s+.*\b{re.escape(target_stem)}\b|import\s+.*\b{re.escape(target_stem)}\b)", content):
                return True
    return False


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
        # Docker compose: ${X}
        if f.name == "docker-compose.yml":
            for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)', content):
                env_vars.append(match.group(1))
    return sorted(set(env_vars))


def check_env_documentation(env_vars: list[str]) -> list[str]:
    if not ENV_EXAMPLE_PATH.exists():
        return ["missing .env.example"]
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    missing = [v for v in env_vars if v not in content]
    if missing:
        return [f"undocumented env vars: {', '.join(missing)}"]
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
    checks = capabilities.get("evidence_checks", {})
    errors: list[str] = []

    for cap in capabilities.get("capabilities", []):
        errors.extend(check_artifacts(cap))
        errors.extend(check_evidence_declared(cap, checks))

    errors.extend(find_unreachable_modules(capabilities.get("entry_points", []), capabilities.get("capabilities", [])))
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

    print("DRIFT CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
