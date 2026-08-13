"""E13 regression tests for permanent verification-state publication."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _publication_job() -> dict[str, object]:
    workflow = yaml.safe_load(_workflow_text())
    return workflow["jobs"]["publish-verification-status"]


def _publication_script() -> str:
    job = _publication_job()
    steps = job["steps"]
    publish_step = next(step for step in steps if step.get("name") == "Publish verified status")
    return publish_step["run"]


def test_publication_is_main_push_only_after_all_producers_succeed() -> None:
    condition = _publication_job()["if"]

    assert "github.event_name == 'push'" in condition
    assert "github.ref == 'refs/heads/main'" in condition
    for job in ("node", "rust", "python", "eval", "integration", "measurability"):
        assert f"needs.{job}.result == 'success'" in condition
    assert "needs['nats-events'].result == 'success'" in condition


def test_publication_uses_one_fixed_lease_guarded_state_branch() -> None:
    script = _publication_script()

    assert "refs/heads/verification-state" in script
    assert "git ls-remote --refs origin" in script
    assert "--force-with-lease=\"$state_ref:$observed_old_oid\"" in script
    assert "GITHUB_RUN_ATTEMPT" not in script
    assert "automation/verification-state-" not in script


def test_publication_has_minimal_permissions_and_never_creates_pr_or_dispatches() -> None:
    workflow = _workflow_text()
    permissions = _publication_job()["permissions"]

    assert permissions == {"contents": "write"}
    assert "pull-requests: write" not in workflow
    assert "actions: write" not in workflow
    assert "gh pr create" not in workflow
    assert "gh workflow run" not in workflow
    assert "git push origin main" not in workflow


def test_publication_consumes_artifact_and_commits_only_generated_state() -> None:
    job = _publication_job()
    steps = job["steps"]
    download = next(step for step in steps if step.get("uses") == "actions/download-artifact@v4")
    script = _publication_script()

    assert download["with"] == {"name": "computed-roadmap", "path": "status-evidence"}
    assert "cp status-evidence/ci-results.json docs/ci-results.json" in script
    assert "python scripts/roadmap_status.py --no-run-commands" in script
    assert "python scripts/roadmap_status.py --check --no-run-commands" in script
    assert "git add docs/ci-results.json docs/ROADMAP.md" in script
    assert 'git commit -m "Update verified capability status"' in script
