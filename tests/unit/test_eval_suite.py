"""Tests for eval-suite case lifecycle and gating."""

import json

import pytest

from scripts import eval_suite


def write_contract(case_dir, contract: dict) -> None:
    case_dir.mkdir(parents=True)
    (case_dir / "contract.json").write_text(json.dumps(contract), encoding="utf-8")


def test_draft_cases_are_excluded_from_metrics_and_gate(monkeypatch, tmp_path) -> None:
    cases_dir = tmp_path / "cases"
    write_contract(
        cases_dir / "draft_case",
        {
            "id": "draft_case",
            "status": "draft",
            "category": "feature",
            "description": "Not runnable yet",
            "base_commit": "none",
            "task": "Draft task",
        },
    )
    monkeypatch.setattr(eval_suite, "CASES_DIR", cases_dir)

    report = eval_suite.run_all()

    assert report.results == []
    assert report.autonomy_rate == 0.0
    assert report.gate_passed is False


def test_draft_case_with_replay_script_is_rejected(monkeypatch, tmp_path) -> None:
    cases_dir = tmp_path / "cases"
    write_contract(
        cases_dir / "runnable_draft",
        {
            "id": "runnable_draft",
            "status": "draft",
            "category": "feature",
            "replay_script": "touch result.txt",
        },
    )
    monkeypatch.setattr(eval_suite, "CASES_DIR", cases_dir)

    with pytest.raises(ValueError, match="draft case runnable_draft appears runnable"):
        eval_suite.run_all()


def test_draft_case_cannot_be_replayed_directly(tmp_path) -> None:
    case_dir = tmp_path / "draft_case"
    write_contract(case_dir, {"id": "draft_case", "status": "draft"})

    with pytest.raises(ValueError, match="draft case draft_case cannot be replayed"):
        eval_suite.run_case(case_dir)
