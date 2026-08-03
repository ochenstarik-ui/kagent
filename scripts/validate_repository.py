from pathlib import Path
import re
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

excluded_parts = {
    ".git",
    ".next",
    "__pycache__",
    "dist",
    "node_modules",
    "target",
}

for path in root.rglob("*"):
    if not path.is_file() or excluded_parts.intersection(path.parts):
        continue
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for pattern in secret_patterns:
        if pattern.search(content):
            errors.append(f"possible secret in {path.relative_to(root)}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"Repository validation passed: {len(required)} required files present")
