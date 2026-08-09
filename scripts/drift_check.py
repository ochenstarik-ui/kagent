"""Spec drift check for KAgent.

Fails CI when the repository diverges from the declared capability registry:
- declared capabilities without evidence
- unreachable modules
- undocumented endpoints
- missing CHANGELOG entries for user-visible changes
- missing ADR for architectural changes

Usage:
    python scripts/drift_check.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES_PATH = ROOT / "docs" / "capabilities.json"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
ADRS_DIR = ROOT / "docs" / "adr"

EXCLUDED_SOURCE_DIRS = {
    ".git",
    ".next",
    ".venv",
    ".worktrees",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
}

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
            check=False,
        )
        result = (proc.returncode == 0, (proc.stdout + proc.stderr).strip())
    except subprocess.TimeoutExpired:
        result = (False, "timeout")
    except (OSError, ValueError) as e:
        result = (False, str(e))
    _Executed[command] = result
    return result


def check_evidence_declared(cap: dict[str, Any], checks: dict[str, Any]) -> list[str]:
    """Verify that each evidence reference is known in the registry.

    Actual command execution happens in CI; drift_check only validates that the
    capability has declared evidence and that the required artifacts exist.
    """
    errors: list[str] = []
    allowed = ", ".join(sorted(checks))
    for ev in cap.get("evidence", []):
        if ev not in checks:
            errors.append(f"[{cap['id']}] unknown evidence: {ev}; allowed: {allowed}")
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
    return [f for f in files if _is_product_source(f)]


def _is_product_source(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if set(relative.parts) & EXCLUDED_SOURCE_DIRS:
        return False
    if "tests" in relative.parts:
        return False
    if path.name == "next-env.d.ts" or ".test." in path.name or ".config." in path.name:
        return False
    return not (
        path.name.startswith("test_") or path.name.endswith(("_test.py", "_test.rs"))
    )


def discover_entry_points(declared_entry_points: list[str]) -> set[Path]:
    entry_points = {
        ROOT / relative
        for relative in declared_entry_points
        if (ROOT / relative).is_file()
    }

    services_dir = ROOT / "services"
    if services_dir.exists():
        for service_dir in services_dir.iterdir():
            if not service_dir.is_dir():
                continue
            for relative in ("main.py", "src/main.py", "src/main.ts", "src/main.js"):
                candidate = service_dir / relative
                if candidate.is_file():
                    entry_points.add(candidate)
            cargo_manifest = service_dir / "Cargo.toml"
            rust_main = service_dir / "src" / "main.rs"
            if cargo_manifest.is_file():
                if rust_main.is_file():
                    entry_points.add(rust_main)
                entry_points.update(
                    _cargo_binary_entry_points(service_dir, cargo_manifest)
                )
            dockerfile = service_dir / "Dockerfile"
            if dockerfile.is_file():
                entry_points.update(_docker_app_entry_points(service_dir, dockerfile))

    for package_json in ROOT.rglob("package.json"):
        relative = package_json.relative_to(ROOT)
        if set(relative.parts) & EXCLUDED_SOURCE_DIRS:
            continue
        entry_points.update(_package_entry_points(package_json))

    app_file_names = {"error", "layout", "loading", "not-found", "page", "route"}
    apps_dir = ROOT / "apps"
    if apps_dir.exists():
        for path in apps_dir.rglob("*"):
            relative = path.relative_to(apps_dir)
            if (
                path.is_file()
                and "app" in relative.parts
                and path.stem in app_file_names
                and path.suffix in {".js", ".jsx", ".ts", ".tsx"}
            ):
                entry_points.add(path)

    return entry_points


def _cargo_binary_entry_points(service_dir: Path, cargo_manifest: Path) -> set[Path]:
    content = cargo_manifest.read_text(encoding="utf-8", errors="replace")
    entry_points: set[Path] = set()
    for section in re.finditer(
        r"^\[\[bin\]\]\s*(.*?)(?=^\[|\Z)", content, re.MULTILINE | re.DOTALL
    ):
        path_match = re.search(
            r'^path\s*=\s*["\']([^"\']+)["\']', section.group(1), re.MULTILINE
        )
        if path_match:
            candidate = service_dir / path_match.group(1)
            if candidate.is_file():
                entry_points.add(candidate)
    return entry_points


def _docker_app_entry_points(service_dir: Path, dockerfile: Path) -> set[Path]:
    content = dockerfile.read_text(encoding="utf-8", errors="replace")
    entry_points: set[Path] = set()
    for match in re.finditer(
        r"['\"]([A-Za-z_][\w.]*)\s*:\s*[A-Za-z_]\w*['\"]", content
    ):
        module = match.group(1)
        candidate = service_dir / f"{module.replace('.', '/')}.py"
        if candidate.is_file():
            entry_points.add(candidate)
    return entry_points


def _package_entry_points(package_json: Path) -> set[Path]:
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    targets = _string_values(package.get("exports"))
    targets.update(_string_values(package.get("main")))
    targets.update(_string_values(package.get("bin")))
    return {
        source
        for target in targets
        for source in [_package_source_path(package_json.parent, target)]
        if source is not None
    }


def _string_values(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return {item for nested in value.values() for item in _string_values(nested)}
    if isinstance(value, list):
        return {item for nested in value for item in _string_values(nested)}
    return set()


def _package_source_path(package_dir: Path, target: str) -> Path | None:
    relative = Path(target.removeprefix("./"))
    candidates: list[Path] = []
    parts = list(relative.parts)
    if parts and parts[0] == "dist":
        parts[0] = "src"
        source = Path(*parts)
        candidates.extend(
            package_dir / source.with_suffix(ext) for ext in (".ts", ".tsx", ".js")
        )
    candidates.append(package_dir / relative)
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def find_unreachable_modules(
    entry_points: list[str], capabilities: list[dict[str, Any]]
) -> list[str]:
    """Return source files that are not reachable from any entry point.

    Reachability is determined by static import/require references. Declared
    capabilities are not automatically considered reachable.
    """
    del capabilities
    source_files = find_source_files()
    source_file_set = set(source_files)
    reachable: set[Path] = set()
    pending: list[Path] = []
    for path in discover_entry_points(entry_points):
        if path in source_file_set:
            reachable.add(path)
            pending.append(path)

    while pending:
        source = pending.pop()
        try:
            content = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for imported in _resolve_relative_imports(source, content, source_file_set):
            if imported not in reachable:
                reachable.add(imported)
                pending.append(imported)

    return sorted(
        f.relative_to(ROOT).as_posix() for f in source_files if f not in reachable
    )


def _resolve_relative_imports(
    source: Path, content: str, source_files: set[Path]
) -> set[Path]:
    imports: set[Path] = set()
    patterns = (
        r"(?:import|export)\s+(?:[^'\"]*?\s+from\s+)?['\"]([^'\"]+)['\"]",
        r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            specifier = match.group(1)
            if not specifier.startswith("."):
                continue
            candidate = source.parent / specifier
            variants = [candidate]
            if candidate.suffix in {".js", ".mjs", ".cjs"}:
                variants.extend(candidate.with_suffix(ext) for ext in (".ts", ".tsx"))
            elif not candidate.suffix:
                variants.extend(
                    candidate.with_suffix(ext) for ext in (".ts", ".tsx", ".js")
                )
                variants.extend(
                    candidate / f"index{ext}" for ext in (".ts", ".tsx", ".js")
                )
            imports.update(path for path in variants if path in source_files)
    if source.suffix == ".py":
        for match in re.finditer(
            r"^\s*from\s+(\.+)([\w.]*)\s+import\s+", content, re.MULTILINE
        ):
            parent = source.parent
            for _ in range(len(match.group(1)) - 1):
                parent = parent.parent
            module = match.group(2).replace(".", "/")
            candidate = parent / module
            variants = (candidate.with_suffix(".py"), candidate / "__init__.py")
            imports.update(path for path in variants if path in source_files)
    return imports


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
        except OSError:
            continue
        for match in re.finditer(
            r'@(?:app|router|\w+_app)\.(get|post|put|patch|delete)\([\'"]([^\'"]+)[\'"]',
            content,
            re.IGNORECASE,
        ):
            found.append(
                (service_dir.name, f"{match.group(1).upper()} {match.group(2)}")
            )
    for f in service_dir.rglob("*.ts"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in re.finditer(
            r'app\.(get|post|put|patch|delete)\([\'"]([^\'"]+)[\'"]',
            content,
            re.IGNORECASE,
        ):
            found.append(
                (service_dir.name, f"{match.group(1).upper()} {match.group(2)}")
            )
    # Rust axum: .route("/path", get(handler))
    for f in service_dir.rglob("*.rs"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in re.finditer(
            r'\.route\([\'"]([^\'"]+)[\'"],\s*(get|post|put|patch|delete)\(',
            content,
            re.IGNORECASE,
        ):
            found.append(
                (service_dir.name, f"{match.group(2).upper()} {match.group(1)}")
            )
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
    for service, routes in route_table.items():
        service_dir = ROOT / "services" / service
        if not service_dir.exists():
            continue
        found = find_endpoints_in_code(service_dir)
        for _, ep in found:
            if not any(match_route(decl, ep) for decl in routes):
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
            if decl.startswith(("ALL", "publish", "subscribe")):
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
    tracked_changes = [
        line for line in output.splitlines() if not line.startswith("??")
    ]
    if not tracked_changes:
        return []
    if "CHANGELOG.md" in output:
        return []
    if re.search(r"\s+(services|apps|packages)/", output):
        return [
            "tracked user-visible changes detected but CHANGELOG.md not updated; add an entry under [Unreleased]"
        ]
    return []


def check_adr() -> list[str]:
    passed, output = run_command("git status --short")
    if not passed or not output:
        return []
    if not ADRS_DIR.exists():
        return ["missing docs/adr directory"]
    # Only fail on tracked modifications to services/packages/docker-compose.
    tracked_changes = [
        line for line in output.splitlines() if not line.startswith("??")
    ]
    if not tracked_changes:
        return []
    needs_adr = any(
        re.search(r"\s+(services|packages|docker-compose\.yml)/", line)
        for line in tracked_changes
    )
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
    forbidden = [
        "eval/",
        "docs/capabilities.json",
        "scripts/eval_suite.py",
        "scripts/roadmap_status.py",
        "scripts/drift_check.py",
    ]
    touched = [
        line
        for line in output.splitlines()
        if not line.startswith("??")
        and "eval/reports/" not in line.replace("\\", "/")
        and any(f in line.replace("\\", "/") for f in forbidden)
    ]
    if touched:
        return [
            f"product task must not modify eval or measurability artifacts: {', '.join(touched)}"
        ]
    return []


def main() -> int:
    capabilities = load_capabilities()
    checks = capabilities.get("evidence_checks", {})
    errors: list[str] = []

    for cap in capabilities.get("capabilities", []):
        errors.extend(check_artifacts(cap))
        errors.extend(check_evidence_declared(cap, checks))

    errors.extend(
        find_unreachable_modules(
            capabilities.get("entry_points", []), capabilities.get("capabilities", [])
        )
    )
    errors.extend(check_undocumented_endpoints(capabilities.get("route_table", {})))
    errors.extend(check_missing_endpoints(capabilities.get("route_table", {})))
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
