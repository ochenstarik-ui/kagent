from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]

required = [
    "README.md",
    "CHANGELOG.md",
    "AGENT_CHANGELOG.md",
    "docs/KAGENT_FULL_PRODUCT_SPEC.md",
    "docs/ARCHITECTURE.md",
    "docs/THREAT_MODEL.md",
    "packages/contracts/src/index.ts",
    "services/control-plane/src/main.ts",
    "services/gateway/src/main.rs",
]

errors = []

for relative in required:
    if not (root / relative).is_file():
        errors.append(f"missing required file: {relative}")

secret_patterns = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
]

tracked_and_unignored = subprocess.run(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    cwd=root,
    check=True,
    capture_output=True,
).stdout.decode("utf-8").split("\0")

for relative in tracked_and_unignored:
    if not relative:
        continue
    path = root / relative
    if not path.is_file():
        continue
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for pattern in secret_patterns:
        if pattern.search(content):
            errors.append(f"possible secret in {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"Repository validation passed: {len(required)} required files present")
