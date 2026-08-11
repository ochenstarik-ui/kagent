"""Behavior tests for deterministic, negative-proof eval replay."""

from __future__ import annotations

import io
import hashlib
import json
import os
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import eval_suite


def write_snapshot(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def test_run_case_requires_empty_and_mutation_negative_proofs(tmp_path: Path) -> None:
    case_dir = tmp_path / "proof_case"
    case_dir.mkdir()
    write_snapshot(case_dir / "base.tar.gz", {"value.txt": "broken\n"})
    (case_dir / "verifier.py").write_text(
        "import pathlib, sys\n"
        "root = pathlib.Path(sys.argv[1])\n"
        "raise SystemExit(0 if (root / 'value.txt').read_text() == 'fixed\\n' else 1)\n",
        encoding="utf-8",
    )
    (case_dir / "cassette.json").write_text(
        json.dumps(
            {
                "response": {"operations": [{"kind": "write", "path": "value.txt", "content": "fixed\n"}]},
                "metrics": {"repair_cycles": 2, "cost_usd": 0.0125},
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "mutation.json").write_text(
        json.dumps({"operations": [{"kind": "write", "path": "value.txt", "content": "mutated\n"}]}),
        encoding="utf-8",
    )
    (case_dir / "contract.json").write_text(
        json.dumps(
            {
                "contract_version": 1,
                "id": "proof_case",
                "category": "bugfix",
                "task": "Fix the value.",
                "snapshot": "base.tar.gz",
                "cassette": "cassette.json",
                "verifier": "verifier.py",
                "mutation": "mutation.json",
                "acceptance": [],
                "expected_artifacts": ["value.txt"],
            }
        ),
        encoding="utf-8",
    )

    result = eval_suite.run_case(case_dir)

    assert result.passed is True
    assert result.empty_diff_rejected is True
    assert result.replay_acceptance_passed is True
    assert result.mutation_rejected is True
    assert result.provider_calls == 0
    assert result.tokens_spent == 0
    assert result.repair_cycles == 2
    assert result.integrated_change_cost_usd == 0.0125


def test_tracked_cases_are_three_runnable_self_contained_replays() -> None:
    case_names = [path.name for path in eval_suite.list_cases()]

    assert case_names == [
        "bugfix_leaky_limiter",
        "feature_add_endpoint",
        "security_fix_header",
    ]
    for case_dir in eval_suite.list_cases():
        contract = eval_suite.load_json(case_dir / "contract.json")
        assert contract.get("status", "active") == "active"
        assert tarfile.is_tarfile(case_dir / contract["snapshot"])
        assert (case_dir / contract["snapshot"]).stat().st_size > 64

    report = eval_suite.run_all()

    assert len(report.results) == 3
    assert report.autonomy_rate == 1.0
    assert report.provider_calls_total == 0
    assert report.tokens_spent_total == 0
    assert all(result["empty_diff_rejected"] for result in report.results)
    assert all(result["replay_acceptance_passed"] for result in report.results)
    assert all(result["mutation_rejected"] for result in report.results)


def test_metrics_schema_declares_replay_proof_and_zero_provider_fields() -> None:
    schema = eval_suite.load_json(eval_suite.METRICS_SCHEMA_PATH)
    report_required = schema["required"]
    result_required = schema["definitions"]["EvalResult"]["required"]

    assert "provider_calls_total" in report_required
    assert "tokens_spent_total" in report_required
    for field in (
        "empty_diff_rejected",
        "replay_acceptance_passed",
        "mutation_rejected",
        "provider_calls",
        "tokens_spent",
        "provider_environment_scrubbed",
    ):
        assert field in result_required


def test_cassette_prompt_hash_matches_recorded_request() -> None:
    for case_dir in eval_suite.list_cases():
        contract = eval_suite.load_json(case_dir / "contract.json")
        cassette = eval_suite.load_json(case_dir / contract["cassette"])
        task = cassette["request"]["task"]
        expected = "sha256:" + hashlib.sha256(task.encode()).hexdigest()

        assert cassette["lookup_key"]["prompt_hash"] == expected


def test_subprocess_environment_is_allowlisted_not_provider_named(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NEW_PROVIDER_API_KEY", "must-not-leak")
    monkeypatch.setenv("UNRELATED_SECRET", "must-not-leak")

    code, output, error = eval_suite.run_shell(
        [
            sys.executable,
            "-c",
            "import os; print(os.getenv('NEW_PROVIDER_API_KEY')); print(os.getenv('UNRELATED_SECRET'))",
        ],
        tmp_path,
    )

    assert code == 0, error
    assert output.splitlines() == ["None", "None"]
    assert "PATH" in os.environ


@pytest.mark.parametrize(
    "value",
    [r"C:\escape.txt", r"folder\escape.txt", "name:stream"],
)
def test_safe_relative_path_rejects_windows_or_colon_paths(value: str) -> None:
    with pytest.raises(ValueError, match="unsafe relative path"):
        eval_suite._safe_relative_path(value)
