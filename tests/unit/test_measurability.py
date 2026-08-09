"""Tests for evidence-backed roadmap status computation."""

import sys

from scripts import roadmap_status


def test_capability_without_evidence_is_printed_as_unverified() -> None:
    registry = {
        "stages": [{"id": "0.1", "name": "Foundation", "status": "complete"}],
        "capabilities": [
            {
                "id": "foundation.bootstrap",
                "stage": "0.1",
                "name": "Bootstrap",
                "evidence": [],
                "artifacts": [],
            }
        ],
        "evidence_checks": {},
    }

    roadmap = roadmap_status.build_roadmap(registry)

    assert "## 0.1 — Foundation [unverified]" in roadmap
    assert "- [ ] [foundation.bootstrap] Bootstrap — unverified" in roadmap


def test_ci_marker_is_not_passing_evidence(monkeypatch, tmp_path) -> None:
    (tmp_path / "CI").touch()
    monkeypatch.setattr(roadmap_status, "ROOT", tmp_path)
    capability = {
        "id": "foundation.bootstrap",
        "evidence": ["ci"],
        "artifacts": [],
    }

    status = roadmap_status.evaluate_capability(
        capability,
        {"ci": {"type": "ci", "job": "build"}},
    )

    assert status.status == "unverified"
    assert status.evidence_results[0].output == "CI result unavailable for job: build"


def test_ci_job_success_is_verifiable_evidence() -> None:
    capability = {
        "id": "foundation.bootstrap",
        "evidence": ["ci"],
        "artifacts": [],
    }

    status = roadmap_status.evaluate_capability(
        capability,
        {"ci": {"type": "ci", "job": "build"}},
        {"jobs": {"build": {"conclusion": "success"}}},
    )

    assert status.status == "verified"
    assert status.evidence_results[0].output == "CI job build: success"


def test_manual_claim_is_not_passing_evidence() -> None:
    status = roadmap_status.evaluate_capability(
        {"id": "foundation.bootstrap", "evidence": ["review"], "artifacts": []},
        {"review": {"type": "manual"}},
    )

    assert status.status == "unverified"
    assert status.evidence_results[0].output == "manual claims are not verifiable evidence"


def test_command_output_with_invalid_utf8_is_replaced() -> None:
    command = f'"{sys.executable}" -c "import sys; sys.stdout.buffer.write(bytes([0xad]))"'

    result = roadmap_status.run_command(command)

    assert result.passed is True
    assert result.output == "�"


def test_build_roadmap_runs_shared_evidence_once(monkeypatch) -> None:
    calls = 0

    def run_command_once(command: str, timeout: float = 120.0) -> roadmap_status.EvidenceResult:
        nonlocal calls
        calls += 1
        return roadmap_status.EvidenceResult(command, True, "passed", 0.0)

    monkeypatch.setattr(roadmap_status, "run_command", run_command_once)
    registry = {
        "stages": [{"id": "0.1", "name": "Foundation"}],
        "capabilities": [
            {"id": "one", "stage": "0.1", "name": "One", "evidence": ["tests"]},
            {"id": "two", "stage": "0.1", "name": "Two", "evidence": ["tests"]},
        ],
        "evidence_checks": {"tests": {"type": "command", "command": "test-command"}},
    }

    roadmap_status.build_roadmap(registry)

    assert calls == 1
