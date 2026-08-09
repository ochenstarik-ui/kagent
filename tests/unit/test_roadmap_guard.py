"""Tests for the generated roadmap manual-edit guard."""

import sys

from scripts import roadmap_status


def test_roadmap_diff_rejects_manual_edit(tmp_path) -> None:
    roadmap_path = tmp_path / "ROADMAP.md"
    roadmap_path.write_text("manual status\n", encoding="utf-8")

    diff = roadmap_status.roadmap_diff("generated status\n", roadmap_path)

    assert diff is not None
    assert "-manual status" in diff
    assert "+generated status" in diff


def test_failed_evidence_output_is_platform_independent() -> None:
    command = f'"{sys.executable}" -c "raise SystemExit(7)"'

    result = roadmap_status.run_command(command)

    assert result.passed is False
    assert result.output == "command failed with exit code 7"


def test_deterministic_roadmap_does_not_execute_commands(monkeypatch) -> None:
    def fail_if_called(command: str, timeout: float = 120.0) -> roadmap_status.EvidenceResult:
        raise AssertionError(f"unexpected command execution: {command} ({timeout})")

    monkeypatch.setattr(roadmap_status, "run_command", fail_if_called)
    registry = {
        "stages": [{"id": "0.1", "name": "Foundation"}],
        "capabilities": [
            {
                "id": "foundation.bootstrap",
                "stage": "0.1",
                "name": "Bootstrap",
                "evidence": ["tests"],
                "artifacts": [],
            }
        ],
        "evidence_checks": {
            "tests": {"type": "command", "command": "platform-dependent-command"}
        },
    }

    roadmap = roadmap_status.build_roadmap(registry, execute_commands=False)

    assert "platform-dependent-command: command evidence not executed" in roadmap
