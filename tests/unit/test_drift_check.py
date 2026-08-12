"""Focused tests for CI drift detection and allowlist policy."""

from datetime import date

import pytest

from scripts import drift_check


def test_known_drift_requires_reason_expiry_and_follow_up_task() -> None:
    data = {
        "version": 1,
        "entries": [
            {
                "path": "services/auth/src/totp.py",
                "reason": "",
            }
        ],
    }

    errors = drift_check.validate_known_drift(data, today=date(2026, 8, 9))

    assert "known drift entry 0 has invalid reason" in errors
    assert "known drift entry 0 has invalid expires" in errors
    assert "known drift entry 0 has invalid follow_up_task" in errors


def test_expired_known_drift_is_rejected() -> None:
    data = {
        "version": 1,
        "entries": [
            {
                "path": "services/auth/src/totp.py",
                "reason": "Not connected to a service entry point.",
                "expires": "2026-08-08",
                "follow_up_task": "KAGENT-AUTH-TOTP-INTEGRATION",
            }
        ],
    }

    errors = drift_check.validate_known_drift(data, today=date(2026, 8, 9))

    assert errors == ["known drift entry 0 expired on 2026-08-08"]


def test_repository_reachability_matches_the_allowlist_exactly() -> None:
    """Detection and the known-drift allowlist must describe the same set.

    The expected set is read from docs/known-drift.json rather than hard-coded,
    so that connecting a module requires removing its allowlist entry in the same
    change. A hard-coded list would need editing by hand on every fix, which is
    exactly the manual bookkeeping this check exists to remove.
    """
    capabilities = drift_check.load_capabilities()

    unreachable = drift_check.find_unreachable_modules(
        capabilities["entry_points"],
        capabilities["capabilities"],
    )

    allowlisted = sorted(entry["path"] for entry in drift_check.load_known_drift()["entries"])

    assert sorted(unreachable) == allowlisted


def test_unknown_unreachable_module_is_rejected() -> None:
    data = {
        "version": 1,
        "entries": [
            {
                "path": "services/auth/src/totp.py",
                "reason": "Not connected to a service entry point.",
                "expires": "2026-09-01",
                "follow_up_task": "KAGENT-AUTH-TOTP-INTEGRATION",
            }
        ],
    }

    errors = drift_check.check_unreachable_drift(
        ["services/auth/src/totp.py", "services/new/src/orphan.py"],
        data,
        today=date(2026, 8, 9),
    )

    assert "unreachable module is not allowlisted: services/new/src/orphan.py" in errors


def test_repository_known_drift_exactly_matches_detection() -> None:
    capabilities = drift_check.load_capabilities()
    unreachable = drift_check.find_unreachable_modules(
        capabilities["entry_points"],
        capabilities["capabilities"],
    )

    errors = drift_check.check_unreachable_drift(
        unreachable,
        drift_check.load_known_drift(),
    )

    assert errors == []


def test_generic_ci_evidence_without_a_job_is_rejected() -> None:
    registry = {
        "capabilities": [{"id": "example", "evidence": ["ci"]}],
        "evidence_checks": {"ci": {"type": "ci"}},
    }

    errors = drift_check.check_evidence_registry(registry, workflow_jobs={"node"})

    assert errors == ["[example] CI evidence ci must name a concrete job"]


def test_repository_evidence_references_are_concrete() -> None:
    errors = drift_check.check_evidence_registry(drift_check.load_capabilities())

    assert errors == []


def test_documented_environment_variable_must_be_read(monkeypatch, tmp_path) -> None:
    env_example = tmp_path / ".env.example"
    env_example.write_text("USED=value\nUNUSED=value\n", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ENV_EXAMPLE_PATH", env_example)

    errors = drift_check.check_env_documentation(["USED"])

    assert errors == ["documented env vars never read: UNUSED"]


@pytest.mark.parametrize("follow_up_task", ["None", "NONE", "-", "n/a", "TBD", ""])
def test_known_drift_rejects_placeholder_follow_up_tasks(follow_up_task: str) -> None:
    data = {
        "version": 1,
        "entries": [
            {
                "path": "services/example/orphan.py",
                "reason": "Pending cleanup.",
                "expires": "2026-09-01",
                "follow_up_task": follow_up_task,
            }
        ],
    }

    errors = drift_check.validate_known_drift(data, today=date(2026, 8, 9))

    assert errors == ["known drift entry 0 has invalid follow_up_task"]


@pytest.mark.parametrize("follow_up_task", ["KAGENT-123", "t_cleanup_tests"])
def test_known_drift_accepts_genuine_follow_up_tasks(follow_up_task: str) -> None:
    data = {
        "version": 1,
        "entries": [
            {
                "path": "services/example/orphan.py",
                "reason": "Pending cleanup.",
                "expires": "2026-09-01",
                "follow_up_task": follow_up_task,
            }
        ],
    }

    assert drift_check.validate_known_drift(data, today=date(2026, 8, 9)) == []


def test_known_drift_rejects_expiry_beyond_90_days() -> None:
    data = {
        "version": 1,
        "entries": [
            {
                "path": "services/example/orphan.py",
                "reason": "Pending cleanup.",
                "expires": "2026-11-08",
                "follow_up_task": "KAGENT-123",
            }
        ],
    }

    errors = drift_check.validate_known_drift(data, today=date(2026, 8, 9))

    assert errors == ["known drift entry 0 expires more than 90 days from 2026-08-09"]


def test_known_drift_accepts_expiry_at_90_days() -> None:
    data = {
        "version": 1,
        "entries": [
            {
                "path": "services/example/orphan.py",
                "reason": "Pending cleanup.",
                "expires": "2026-11-07",
                "follow_up_task": "KAGENT-123",
            }
        ],
    }

    assert drift_check.validate_known_drift(data, today=date(2026, 8, 9)) == []


def test_nested_conftest_is_an_implicit_runner_entrypoint(monkeypatch, tmp_path) -> None:
    conftest = tmp_path / "services" / "example" / "nested" / "conftest.py"
    conftest.parent.mkdir(parents=True)
    conftest.write_text("pytest_plugins = []\n", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    unreachable = drift_check.find_unreachable_modules([], [])

    assert "services/example/nested/conftest.py" not in unreachable


@pytest.mark.parametrize(
    ("config_body", "runner_file"),
    [
        ("testDir: './browser-tests'", "smoke.spec.ts"),
        ("testDir: './browser-tests', testMatch: '**/*.pw.ts'", "smoke.pw.ts"),
        ("testDir: './browser-tests', testMatch: ['**/*.pw.ts']", "smoke.pw.ts"),
    ],
)
def test_playwright_config_derives_runner_entrypoints(
    monkeypatch,
    tmp_path,
    config_body: str,
    runner_file: str,
) -> None:
    app = tmp_path / "apps" / "frontend"
    test_dir = app / "browser-tests"
    test_dir.mkdir(parents=True)
    (app / "playwright.config.ts").write_text(
        f"export default defineConfig({{{config_body}}});\n",
        encoding="utf-8",
    )
    (test_dir / runner_file).write_text("export {};\n", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    unreachable = drift_check.find_unreachable_modules([], [])

    assert f"apps/frontend/browser-tests/{runner_file}" not in unreachable


def test_unimported_service_module_remains_unreachable(monkeypatch, tmp_path) -> None:
    orphan = tmp_path / "services" / "example" / "orphan.py"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(drift_check, "ROOT", tmp_path)

    unreachable = drift_check.find_unreachable_modules([], [])

    assert unreachable == ["services/example/orphan.py"]
