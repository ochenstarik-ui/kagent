"""E13 regression tests for permanent verification-state publication."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _publication_job_text() -> str:
    workflow = _workflow_text()
    marker = "  publish-verification-status:\n"
    assert workflow.count(marker) == 1
    return workflow.split(marker, 1)[1]


def _publication_script() -> str:
    job = _publication_job_text()
    marker = "      - name: Publish verified status\n"
    assert job.count(marker) == 1
    return job.split(marker, 1)[1]


def test_publication_is_main_push_only_after_all_producers_succeed() -> None:
    job = _publication_job_text()

    assert "github.event_name == 'push'" in job
    assert "github.ref == 'refs/heads/main'" in job
    for producer in (
        "node",
        "rust",
        "python",
        "eval",
        "integration",
        "measurability",
    ):
        assert f"needs.{producer}.result == 'success'" in job
    assert "needs['nats-events'].result == 'success'" in job


def test_publication_uses_one_fixed_lease_guarded_state_branch() -> None:
    script = _publication_script()

    assert "refs/heads/verification-state" in script
    assert "git ls-remote --refs origin" in script
    assert "--force-with-lease=" in script
    assert "$state_ref:$observed_old_oid" in script
    assert "GITHUB_RUN_ATTEMPT" not in script
    assert "automation/verification-state-" not in script


def test_publication_has_minimal_permissions_and_never_creates_pr_or_dispatches() -> None:
    workflow = _workflow_text()
    job = _publication_job_text()
    permissions = job.split("    permissions:\n", 1)[1].split("    steps:\n", 1)[0]

    assert permissions.strip() == "contents: write"
    assert "pull-requests: write" not in workflow
    assert "actions: write" not in workflow
    assert "gh pr create" not in workflow
    assert "gh workflow run" not in workflow
    assert "git push origin main" not in workflow


def test_publication_consumes_artifact_and_commits_only_generated_state() -> None:
    job = _publication_job_text()
    script = _publication_script()

    assert "uses: actions/download-artifact@v4" in job
    assert "name: computed-roadmap" in job
    assert "path: status-evidence" in job
    assert "cp status-evidence/ci-results.json docs/ci-results.json" in script
    assert "python scripts/roadmap_status.py --no-run-commands" in script
    assert "python scripts/roadmap_status.py --check --no-run-commands" in script
    assert "git add docs/ci-results.json docs/ROADMAP.md" in script
    assert 'git commit -m "Update verified capability status"' in script
