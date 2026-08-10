"""Verify CI workflow does not use per-file test selection.

The python job must run entire directories, not a hand-curated file list.
"""

from pathlib import Path

import yaml


def test_python_job_has_no_selected_file_list() -> None:
    """CI python job must not list individual test files."""
    ci_path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
    with ci_path.open() as f:
        ci = yaml.safe_load(f)

    python_job = ci["jobs"]["python"]
    steps_text = yaml.dump(python_job["steps"])

    # Must reference directory paths, not individual .py files
    assert "tests/unit" in steps_text, "Python job must include tests/unit directory"
    # Must NOT have individual file references like test_foo.py in the run command
    import re
    run_steps = [s.get("run", "") for s in python_job["steps"] if "run" in s]
    pytest_runs = [r for r in run_steps if "pytest" in r]
    for run_cmd in pytest_runs:
        # Should not contain specific .py file paths (like tests/unit/test_foo.py)
        matches = re.findall(r'tests/unit/test_\w+\.py', run_cmd)
        assert not matches, f"Found per-file test selection: {matches}"
