"""Focused tests for product-code reachability in the drift check."""

from scripts import drift_check


def test_transitively_reachable_file_is_not_reported(monkeypatch, tmp_path) -> None:
    source_dir = tmp_path / "packages" / "example" / "src"
    source_dir.mkdir(parents=True)
    (source_dir / "index.ts").write_text(
        'export * from "./first.js";\n', encoding="utf-8"
    )
    (source_dir / "first.ts").write_text(
        'export * from "./second.js";\n', encoding="utf-8"
    )
    (source_dir / "second.ts").write_text("export const value = 1;\n", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    unreachable = drift_check.find_unreachable_modules(
        ["packages/example/src/index.ts"], []
    )

    assert unreachable == []


def test_file_reachable_only_from_test_is_reported(monkeypatch, tmp_path) -> None:
    source_dir = tmp_path / "service" / "src"
    tests_dir = tmp_path / "tests" / "unit"
    source_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    (source_dir / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tests_dir / "test_feature.py").write_text(
        "from service.src import feature\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    unreachable = drift_check.find_unreachable_modules([], [])

    assert unreachable == ["service/src/feature.py"]


def test_generated_and_dependency_directories_are_not_scanned(
    monkeypatch, tmp_path
) -> None:
    excluded_dirs = (
        ".git",
        ".next",
        ".venv",
        ".worktrees",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
    )
    for directory in excluded_dirs:
        generated = tmp_path / directory / "nested"
        generated.mkdir(parents=True)
        (generated / "ignored.py").write_text("VALUE = 1\n", encoding="utf-8")
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source = source_dir / "main.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    assert drift_check.find_source_files() == [source]


def test_product_entry_points_are_discovered_from_manifests_and_conventions(
    monkeypatch,
    tmp_path,
) -> None:
    files = {
        "services/gateway/Cargo.toml": '[package]\nname = "gateway"\n',
        "services/gateway/src/main.rs": "fn main() {}\n",
        "services/worker/Cargo.toml": '[[bin]]\nname = "worker"\npath = "cmd/worker.rs"\n',
        "services/worker/cmd/worker.rs": "fn main() {}\n",
        "services/control/src/main.ts": "export {};\n",
        "services/reasoning/main.py": "pass\n",
        "services/reasoning/Dockerfile": 'CMD ["uvicorn", "src.server:app"]\n',
        "services/reasoning/src/server.py": "app = object()\n",
        "packages/contracts/package.json": '{"exports": {".": "./dist/index.js"}}\n',
        "packages/contracts/src/index.ts": "export {};\n",
        "apps/web/app/page.tsx": "export default function Page() {}\n",
        "apps/web/app/layout.tsx": "export default function Layout() {}\n",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    entry_points = drift_check.discover_entry_points([])

    assert entry_points == {
        tmp_path / "apps/web/app/layout.tsx",
        tmp_path / "apps/web/app/page.tsx",
        tmp_path / "packages/contracts/src/index.ts",
        tmp_path / "services/control/src/main.ts",
        tmp_path / "services/gateway/src/main.rs",
        tmp_path / "services/reasoning/main.py",
        tmp_path / "services/reasoning/src/server.py",
        tmp_path / "services/worker/cmd/worker.rs",
    }


def test_built_package_export_prefers_source_and_follows_export_stars(
    monkeypatch,
    tmp_path,
) -> None:
    package_dir = tmp_path / "packages" / "contracts"
    files = {
        "package.json": '{"exports": {".": "./dist/index.js"}}\n',
        "dist/index.js": 'export * from "./artifact.js";\n',
        "src/index.ts": (
            'export * from "./artifact.js";\n'
            'export * from "./event.js";\n'
            'export * from "./ids.js";\n'
            'export * from "./task.js";\n'
        ),
        "src/artifact.ts": "export const artifact = 1;\n",
        "src/event.ts": "export const event = 1;\n",
        "src/ids.ts": "export const id = 1;\n",
        "src/task.ts": "export const task = 1;\n",
        "src/reasoning.ts": "export const reasoning = 1;\n",
    }
    for relative, content in files.items():
        path = package_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    assert drift_check.discover_entry_points([]) == {package_dir / "src/index.ts"}
    assert drift_check.find_unreachable_modules([], []) == [
        "packages/contracts/src/reasoning.ts"
    ]


def test_python_relative_imports_are_followed_from_docker_app(
    monkeypatch, tmp_path
) -> None:
    service_dir = tmp_path / "services" / "reasoning"
    source_dir = service_dir / "src"
    source_dir.mkdir(parents=True)
    (service_dir / "Dockerfile").write_text(
        'CMD ["uvicorn", "src.server:app"]\n',
        encoding="utf-8",
    )
    (source_dir / "server.py").write_text(
        "from .engine import Engine\napp = object()\n", encoding="utf-8"
    )
    (source_dir / "engine.py").write_text("class Engine:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    assert drift_check.find_unreachable_modules([], []) == []


def test_unknown_evidence_lists_allowed_names() -> None:
    capability = {"id": "web.dashboard", "evidence": ["deploy"]}
    checks = {"build": {"type": "command"}, "ci": {"type": "ci"}}

    assert drift_check.check_evidence_declared(capability, checks) == [
        "[web.dashboard] unknown evidence: deploy; allowed: build, ci"
    ]


def test_generated_eval_report_does_not_change_drift_result(monkeypatch) -> None:
    monkeypatch.setattr(
        drift_check,
        "run_command",
        lambda command: (True, " M eval/reports/latest.json"),
    )

    assert drift_check.check_forbidden_paths() == []


def test_main_does_not_report_code_env_vars_missing_from_example(
    monkeypatch, tmp_path, capsys
) -> None:
    source = tmp_path / "services" / "example" / "src" / "main.py"
    source.parent.mkdir(parents=True)
    source.write_text('import os\nos.getenv("UNDOCUMENTED")\n', encoding="utf-8")
    (tmp_path / ".env.example").write_text("", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)
    monkeypatch.setattr(
        drift_check,
        "load_capabilities",
        lambda: {"capabilities": [], "entry_points": [], "route_table": {}},
    )
    monkeypatch.setattr(drift_check, "find_unreachable_modules", lambda *_: [])
    monkeypatch.setattr(drift_check, "check_changelog", list)
    monkeypatch.setattr(drift_check, "check_adr", list)
    monkeypatch.setattr(drift_check, "check_forbidden_paths", list)

    assert drift_check.main() == 0
    assert "undocumented env vars" not in capsys.readouterr().err
