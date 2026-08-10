"""Focused tests for CI drift detection and allowlist policy."""

from datetime import date

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
