"""Regression tests for the Python CI test-suite scope."""

import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _python_job() -> str:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"(?ms)^  python:\s*$\n(?P<body>.*?)(?=^  [\w-]+:\s*$|\Z)",
        workflow,
    )
    assert match is not None, "CI workflow must define a python job"
    return match.group("body")


def _run_commands(job: str) -> list[str]:
    lines = job.splitlines()
    commands: list[str] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(?P<indent>\s*)(?:-\s+)?run:\s*(?P<value>.*)$", line)
        if match is None:
            continue

        value = match.group("value").strip()
        if value not in {"|", "|-", ">", ">-"}:
            commands.append(value)
            continue

        indent = len(match.group("indent"))
        continuation: list[str] = []
        for following in lines[index + 1 :]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            continuation.append(following.strip())
        commands.append(" ".join(continuation))
    return commands


def test_python_ci_runs_all_unit_test_directories_without_named_files() -> None:
    pytest_commands = [
        re.sub(r"\s+", " ", command).strip()
        for command in _run_commands(_python_job())
        if re.search(r"\bpython\s+-m\s+pytest\b", command)
    ]

    assert len(pytest_commands) == 1, "python job must invoke pytest exactly once"
    pytest_command = pytest_commands[0]
    arguments = set(shlex.split(pytest_command))
    expected_directories = {
        "tests/unit",
        "services/reasoning-engine/tests/unit",
        "services/pipeline/tests/unit",
    }

    assert expected_directories <= arguments
    assert re.search(r"(?:^|\s)tests/unit/test_[^\s]*\.py(?:\s|$)", pytest_command) is None
    assert not ({"--ignore", "--deselect", "-k"} & arguments)
    assert not any(
        argument.startswith(("--ignore=", "--deselect=", "-k="))
        for argument in arguments
    )


def test_python_ci_ruff_uses_repository_policy_for_all_python_scopes() -> None:
    ruff_commands = [
        shlex.split(re.sub(r"\s+", " ", command).strip())
        for command in _run_commands(_python_job())
        if re.search(r"\bruff\s+check\b", command)
    ]

    assert ruff_commands == [["ruff", "check", "services", "scripts", "tests"]]
