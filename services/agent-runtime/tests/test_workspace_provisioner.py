from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from task_contract import TaskExecutionContract
from workspace_provisioner import GitWorkspaceProvisioner


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def contract_payload() -> dict[str, object]:
    return {
        "schemaVersion": "1",
        "projectId": "project-1",
        "taskId": "task-1",
        "objective": "Implement the provisioner",
        "contextRefs": [],
        "allowedPaths": ["src/**", "README.md"],
        "requiredChecks": ["python -m unittest"],
        "limits": {
            "maxRuntimeMinutes": 60,
            "maxChangedFiles": 20,
            "maxConcurrentAgents": 1,
            "networkAccess": "denied",
        },
        "issuedAt": "2026-08-03T00:00:00.000Z",
    }


class TaskContractTests(unittest.TestCase):
    def test_digest_and_path_enforcement(self) -> None:
        payload = contract_payload()
        expected = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        contract = TaskExecutionContract.model_validate(payload)

        contract.assert_digest(expected)
        self.assertTrue(contract.allows_path("src/worker.py"))
        self.assertTrue(contract.allows_path("README.md"))
        self.assertFalse(contract.allows_path("../secret"))
        self.assertFalse(contract.allows_path("docs/plan.md"))
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            contract.assert_digest("0" * 64)

        invalid = contract_payload()
        invalid["taskId"] = "../escape"
        with self.assertRaises(ValueError):
            TaskExecutionContract.model_validate(invalid)


class GitWorkspaceProvisionerTests(unittest.TestCase):
    def test_create_recover_and_cleanup_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="kagent-provisioner-test-",
            dir=os.getenv("KAGENT_TEST_TMP"),
        ) as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            git("init", "-b", "main", cwd=source)
            git("config", "user.email", "tests@kagent.dev", cwd=source)
            git("config", "user.name", "KAgent Tests", cwd=source)
            (source / "README.md").write_text("fixture\n", encoding="utf-8")
            git("add", "README.md", cwd=source)
            git("commit", "-m", "fixture", cwd=source)

            provisioner = GitWorkspaceProvisioner(
                root / "runtime",
                allow_local_repositories=True,
            )
            first = provisioner.provision(
                "workspace-1",
                str(source),
                "main",
                "agent/workspace-test",
            )
            second = provisioner.provision(
                "workspace-1",
                str(source),
                "main",
                "agent/workspace-test",
            )

            self.assertFalse(first.recovered)
            self.assertTrue(second.recovered)
            self.assertEqual(first.head_sha, second.head_sha)
            self.assertEqual(first.checkout_ref, "checkout:workspace-1")
            self.assertTrue(provisioner.cleanup("workspace-1", str(source)))
            self.assertFalse(provisioner.cleanup("workspace-1", str(source)))


if __name__ == "__main__":
    unittest.main()
