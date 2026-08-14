from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_repository_validator_uses_git_ignore_boundaries() -> None:
    source = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    assert '"ls-files"' in source
    assert '"--exclude-standard"' in source
    assert 'root.rglob("*")' not in source
