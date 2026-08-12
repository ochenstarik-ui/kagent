"""E7 contract tests for tracked, main-only verification evidence."""

import json
import sys
from pathlib import Path

import pytest

from scripts import ci_results, roadmap_status


ROOT = Path(__file__).resolve().parents[2]


def _metadata() -> dict[str, str]:
    return {
        "run_id": "4242",
        "commit": "0123456789abcdef",
        "timestamp": "2026-08-10T12:00:00Z",
        "run_url": "https://github.com/ochenstarik-ui/kagent/actions/runs/4242",
        "event": "push",
        "ref": "refs/heads/main",
    }


def _registry(evidence: dict[str, object]) -> dict[str, object]:
    return {
        "stages": [{"id": "0.1", "name": "Foundation"}],
        "capabilities": [
            {
                "id": "foundation.bootstrap",
                "stage": "0.1",
                "name": "Bootstrap",
                "evidence": ["unit_tests", "node_ci"],
                "artifacts": [],
            }
        ],
        "evidence_checks": {
            "unit_tests": {"type": "command", "command": "pnpm test"},
            "node_ci": {"type": "ci", "job": "node"},
        },
        "_ci_results": evidence,
    }


def _evidence(**metadata_overrides: str) -> dict[str, object]:
    metadata = {**_metadata(), **metadata_overrides}
    return ci_results.build_ci_results(
        {
            "node": {
                "result": "success",
                "outputs": {"commands": '["pnpm test"]'},
            }
        },
        **metadata,
    )


def test_successful_main_push_evidence_verifies_with_provenance() -> None:
    evidence = _evidence()

    roadmap = roadmap_status.build_roadmap(
        _registry(evidence), execute_commands=False
    )

    assert evidence["run"]["event"] == "push"
    assert evidence["run"]["ref"] == "refs/heads/main"
    assert "Bootstrap — verified" in roadmap
    assert "[CI run 4242]" in roadmap
    assert "commit `0123456`" in roadmap
    assert "2026-08-10T12:00:00Z" in roadmap


@pytest.mark.parametrize(
    ("event", "ref"),
    [
        ("push", "refs/heads/feature"),
        ("pull_request", "refs/pull/17/merge"),
    ],
)
def test_non_main_evidence_never_verifies(event: str, ref: str) -> None:
    roadmap = roadmap_status.build_roadmap(
        _registry(_evidence(event=event, ref=ref)), execute_commands=False
    )

    assert "Bootstrap — unverified" in roadmap
    assert "invalid CI provenance" in roadmap


def test_missing_result_never_verifies() -> None:
    evidence = _evidence()
    del evidence["commands"]["pnpm test"]

    roadmap = roadmap_status.build_roadmap(
        _registry(evidence), execute_commands=False
    )

    assert "Bootstrap — partial" in roadmap
    assert "pnpm test: command evidence not executed" in roadmap


@pytest.mark.parametrize("conclusion", ["failure", "skipped", "cancelled"])
def test_non_successful_results_remain_unverified(conclusion: str) -> None:
    evidence = _evidence()
    evidence["jobs"]["node"]["conclusion"] = conclusion
    evidence["commands"]["pnpm test"]["conclusion"] = conclusion

    roadmap = roadmap_status.build_roadmap(
        _registry(evidence), execute_commands=False
    )

    assert "Bootstrap — unverified" in roadmap


def test_mismatched_sha_never_verifies() -> None:
    evidence = _evidence()
    evidence["commands"]["pnpm test"]["commit"] = "fedcba9876543210"

    roadmap = roadmap_status.build_roadmap(
        _registry(evidence), execute_commands=False
    )

    assert "Bootstrap — partial" in roadmap
    assert "invalid CI provenance" in roadmap


def test_malformed_result_never_verifies() -> None:
    evidence = _evidence()
    evidence["jobs"]["node"] = "success"

    roadmap = roadmap_status.build_roadmap(
        _registry(evidence), execute_commands=False
    )

    assert "Bootstrap — partial" in roadmap
    assert "invalid CI result" in roadmap


def test_no_run_commands_loads_tracked_evidence_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    capabilities_path = tmp_path / "capabilities.json"
    evidence_path = tmp_path / "ci-results.json"
    roadmap_path = tmp_path / "ROADMAP.md"
    capabilities_path.write_text(json.dumps(_registry({}) | {"_ci_results": None}))
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")

    monkeypatch.setattr(roadmap_status, "CAPABILITIES_PATH", capabilities_path)
    monkeypatch.setattr(roadmap_status, "CI_RESULTS_PATH", evidence_path)
    monkeypatch.setattr(roadmap_status, "ROADMAP_PATH", roadmap_path)
    monkeypatch.setattr(sys, "argv", ["roadmap_status.py", "--no-run-commands"])

    assert roadmap_status.main() == 0
    assert "Bootstrap — verified" in roadmap_path.read_text(encoding="utf-8")


def test_workflow_publishes_main_evidence_only_through_pr() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in workflow
    assert "github.event_name == 'push'" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    for job in ("node", "rust", "python", "eval", "integration"):
        assert f"needs.{job}.result == 'success'" in workflow
    assert "needs['nats-events'].result == 'success'" in workflow
    assert "needs.measurability.result == 'success'" in workflow
    assert "publish-verification-status:" in workflow
    measurability = workflow.split("  measurability:", 1)[1].split(
        "  nats-events:", 1
    )[0]
    assert "contents: write" not in measurability
    assert "pull-requests: write" not in measurability
    assert "actions: write" not in measurability
    assert "contents: write" in workflow
    assert "pull-requests: write" in workflow
    assert "actions: write" in workflow
    assert "GH_TOKEN: ${{ github.token }}" in workflow
    assert "git add docs/ci-results.json docs/ROADMAP.md" in workflow
    assert 'git push origin "$branch"' in workflow
    assert 'gh pr create --base main --head "$branch"' in workflow
    assert 'gh workflow run ci.yml --ref "$branch"' in workflow
    assert "git push origin main" not in workflow
    assert "--force" not in workflow
    assert "gh pr merge" not in workflow
    assert "pull_request_target" not in workflow
