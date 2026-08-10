"""Tests for CI run evidence collection and roadmap consumption."""

import json
from pathlib import Path

import pytest

from scripts import ci_results, roadmap_status


ROOT = Path(__file__).resolve().parents[2]


def _run_metadata() -> dict[str, str]:
    return {
        "run_id": "4242",
        "commit": "0123456789abcdef",
        "timestamp": "2026-08-10T12:00:00Z",
        "run_url": "https://github.com/ochenstarik-ui/kagent/actions/runs/4242",
    }


def test_collects_job_results_and_executed_commands() -> None:
    needs = {
        "node": {
            "result": "success",
            "outputs": {"commands": '["pnpm typecheck", "pnpm test"]'},
        },
        "rust": {
            "result": "failure",
            "outputs": {
                "commands": '["cargo test --manifest-path services/gateway/Cargo.toml"]'
            },
        },
    }

    results = ci_results.build_ci_results(needs, **_run_metadata())

    assert results["jobs"]["node"] == {
        "name": "node",
        "conclusion": "success",
        "run_id": "4242",
        "commit": "0123456789abcdef",
        "timestamp": "2026-08-10T12:00:00Z",
        "url": "https://github.com/ochenstarik-ui/kagent/actions/runs/4242",
    }
    assert results["commands"]["pnpm test"]["conclusion"] == "success"
    assert results["commands"][
        "cargo test --manifest-path services/gateway/Cargo.toml"
    ]["conclusion"] == "failure"


def test_collects_each_command_outcome_from_a_failed_job() -> None:
    needs = {
        "node": {
            "result": "failure",
            "outputs": {
                "commands": (
                    '{"pnpm typecheck":"success","pnpm test":"failure",'
                    '"pnpm build":"skipped"}'
                )
            },
        }
    }

    results = ci_results.build_ci_results(needs, **_run_metadata())

    assert results["commands"]["pnpm typecheck"]["conclusion"] == "success"
    assert results["commands"]["pnpm test"]["conclusion"] == "failure"
    assert results["commands"]["pnpm build"]["conclusion"] == "skipped"


def test_green_job_and_command_verify_capability_with_run_link() -> None:
    ci_evidence = ci_results.build_ci_results(
        {
            "node": {
                "result": "success",
                "outputs": {"commands": '["pnpm test"]'},
            }
        },
        **_run_metadata(),
    )
    registry = {
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
        "_ci_results": ci_evidence,
    }

    roadmap = roadmap_status.build_roadmap(registry, execute_commands=False)

    assert "- [x] [foundation.bootstrap] Bootstrap — verified" in roadmap
    assert "[CI run 4242](https://github.com/ochenstarik-ui/kagent/actions/runs/4242)" in roadmap
    assert "commit `0123456`" in roadmap


def test_missing_job_result_keeps_capability_unverified() -> None:
    status = roadmap_status.evaluate_capability(
        {"id": "foundation.bootstrap", "evidence": ["node_ci"], "artifacts": []},
        {"node_ci": {"type": "ci", "job": "node"}},
        {"jobs": {}},
        execute_commands=False,
    )

    assert status.status == "unverified"
    assert status.evidence_results[0].output == "CI result unavailable for job: node"


def test_partial_capability_lists_missing_evidence() -> None:
    ci_evidence = ci_results.build_ci_results(
        {
            "node": {
                "result": "success",
                "outputs": {"commands": '["pnpm test"]'},
            }
        },
        **_run_metadata(),
    )
    registry = {
        "stages": [{"id": "0.1", "name": "Foundation"}],
        "capabilities": [
            {
                "id": "foundation.bootstrap",
                "stage": "0.1",
                "name": "Bootstrap",
                "evidence": ["unit_tests", "rust_ci"],
                "artifacts": [],
            }
        ],
        "evidence_checks": {
            "unit_tests": {"type": "command", "command": "pnpm test"},
            "rust_ci": {"type": "ci", "job": "rust"},
        },
        "_ci_results": ci_evidence,
    }

    roadmap = roadmap_status.build_roadmap(registry, execute_commands=False)

    assert "- [ ] [foundation.bootstrap] Bootstrap — partial" in roadmap
    assert "rust_ci: CI result unavailable for job: rust" in roadmap


def test_failed_job_does_not_verify_its_command_evidence() -> None:
    ci_evidence = ci_results.build_ci_results(
        {
            "node": {
                "result": "failure",
                "outputs": {"commands": '["pnpm test"]'},
            }
        },
        **_run_metadata(),
    )

    status = roadmap_status.evaluate_capability(
        {"id": "foundation.bootstrap", "evidence": ["unit_tests"], "artifacts": []},
        {"unit_tests": {"type": "command", "command": "pnpm test"}},
        ci_evidence,
        execute_commands=False,
    )

    assert status.status == "unverified"
    assert status.evidence_results[0].output == "CI command pnpm test (node): failure"


def test_skipped_command_does_not_verify_command_evidence() -> None:
    ci_evidence = ci_results.build_ci_results(
        {
            "node": {
                "result": "failure",
                "outputs": {"commands": '{"pnpm test":"skipped"}'},
            }
        },
        **_run_metadata(),
    )

    result = roadmap_status.evaluate_ci_command("pnpm test", ci_evidence)

    assert result.passed is False
    assert result.output == "CI command pnpm test (node): skipped"


@pytest.mark.parametrize("missing_field", ["run_id", "commit", "timestamp", "url"])
def test_success_without_complete_provenance_stays_unverified(
    missing_field: str,
) -> None:
    evidence = ci_results.build_ci_results(
        {
            "node": {
                "result": "success",
                "outputs": {"commands": '{"pnpm test":"success"}'},
            }
        },
        **_run_metadata(),
    )
    del evidence["commands"]["pnpm test"][missing_field]

    result = roadmap_status.evaluate_ci_command("pnpm test", evidence)

    assert result.passed is False
    assert "invalid CI provenance" in result.output


def test_mismatched_command_sha_stays_unverified() -> None:
    evidence = ci_results.build_ci_results(
        {
            "node": {
                "result": "success",
                "outputs": {"commands": '{"pnpm test":"success"}'},
            }
        },
        **_run_metadata(),
    )
    evidence["commands"]["pnpm test"]["commit"] = "different-commit"

    result = roadmap_status.evaluate_ci_command("pnpm test", evidence)

    assert result.passed is False
    assert "invalid CI provenance" in result.output


def test_malformed_ci_results_stay_unverified() -> None:
    assert roadmap_status.evaluate_ci_job("node", {"jobs": []}).passed is False
    assert roadmap_status.evaluate_ci_command(
        "pnpm test", {"commands": {"pnpm test": ["success"]}}
    ).passed is False


def test_duplicate_command_evidence_never_upgrades_failure() -> None:
    evidence = ci_results.build_ci_results(
        {
            "node": {
                "result": "failure",
                "outputs": {"commands": '{"pnpm test":"failure"}'},
            },
            "integration": {
                "result": "success",
                "outputs": {"commands": '{"pnpm test":"success"}'},
            },
        },
        **_run_metadata(),
    )

    result = roadmap_status.evaluate_ci_command("pnpm test", evidence)

    assert result.passed is False
    assert evidence["commands"]["pnpm test"]["conclusion"] == "ambiguous"


def test_missing_artifact_prevents_verified_status() -> None:
    status = roadmap_status.CapabilityStatus(
        capability={"id": "foundation.bootstrap"},
        evidence_results=[
            roadmap_status.EvidenceResult("node", True, "success", 0.0)
        ],
        missing_artifacts=["missing.txt"],
    )

    assert status.status == "partial"
    assert status.passed is False


def test_collector_rejects_incomplete_run_provenance() -> None:
    metadata = _run_metadata()
    metadata["run_id"] = ""

    with pytest.raises(ValueError, match="run provenance"):
        ci_results.build_ci_results({}, **metadata)


def test_collector_rejects_malformed_command_output() -> None:
    needs = {
        "node": {
            "result": "success",
            "outputs": {"commands": "not-json"},
        }
    }

    with pytest.raises(ValueError, match="valid JSON"):
        ci_results.build_ci_results(needs, **_run_metadata())


def test_workflow_executes_and_publishes_every_registry_command() -> None:
    registry = json.loads(
        (ROOT / "docs" / "capabilities.json").read_text(encoding="utf-8")
    )
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    commands = {
        check["command"]
        for check in registry["evidence_checks"].values()
        if check.get("type") == "command"
    }

    missing = sorted(command for command in commands if workflow.count(command) < 2)

    assert missing == [], f"commands must be both executed and published: {missing}"


def test_ci_results_file_requires_run_provenance(tmp_path) -> None:
    evidence_path = tmp_path / "ci-results.json"
    evidence_path.write_text(
        '{"jobs":{"node":{"conclusion":"success"}}}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="run provenance"):
        roadmap_status.load_ci_results(evidence_path)


def test_deterministic_roadmap_rejects_legacy_job_without_provenance() -> None:
    registry = {
        "stages": [{"id": "0.1", "name": "Foundation"}],
        "capabilities": [
            {
                "id": "foundation.bootstrap",
                "stage": "0.1",
                "name": "Bootstrap",
                "evidence": ["node_ci"],
                "artifacts": [],
            }
        ],
        "evidence_checks": {"node_ci": {"type": "ci", "job": "node"}},
        "_ci_results": {"jobs": {"node": {"conclusion": "success"}}},
    }

    roadmap = roadmap_status.build_roadmap(registry, execute_commands=False)

    assert "Bootstrap — unverified" in roadmap
    assert "invalid CI provenance" in roadmap
