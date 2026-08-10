"""Collect GitHub Actions job conclusions into roadmap CI evidence JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _commands_from_outputs(
    outputs: object, default_conclusion: str
) -> dict[str, str]:
    if not isinstance(outputs, dict):
        return {}
    raw_commands = outputs.get("commands", "[]")
    if isinstance(raw_commands, str):
        try:
            parsed = json.loads(raw_commands)
        except json.JSONDecodeError as exc:
            raise ValueError("job output 'commands' must be valid JSON") from exc
    else:
        parsed = raw_commands
    if isinstance(parsed, list) and all(
        isinstance(command, str) and command for command in parsed
    ):
        return {command: default_conclusion for command in parsed}
    if isinstance(parsed, dict) and all(
        isinstance(command, str)
        and command
        and isinstance(conclusion, str)
        and conclusion
        for command, conclusion in parsed.items()
    ):
        return parsed
    raise ValueError(
        "job output 'commands' must map non-empty commands to conclusions"
    )


def build_ci_results(
    needs: dict[str, Any],
    *,
    run_id: str,
    commit: str,
    timestamp: str,
    run_url: str,
) -> dict[str, Any]:
    """Normalize the Actions needs context and attach run provenance."""
    provenance = (run_id, commit, timestamp, run_url)
    if any(not isinstance(value, str) or not value for value in provenance):
        raise ValueError("run provenance fields must be non-empty strings")
    run = {
        "id": run_id,
        "commit": commit,
        "timestamp": timestamp,
        "url": run_url,
    }
    jobs: dict[str, dict[str, str]] = {}
    commands: dict[str, dict[str, str]] = {}

    for job_name, raw_job in needs.items():
        job = raw_job if isinstance(raw_job, dict) else {}
        conclusion = str(job.get("result", "unknown"))
        evidence = {
            "name": job_name,
            "conclusion": conclusion,
            "run_id": run_id,
            "commit": commit,
            "timestamp": timestamp,
            "url": run_url,
        }
        jobs[job_name] = evidence
        for command, command_conclusion in _commands_from_outputs(
            job.get("outputs"), conclusion
        ).items():
            command_evidence = {
                "conclusion": command_conclusion,
                "job": job_name,
                "run_id": run_id,
                "commit": commit,
                "timestamp": timestamp,
                "url": run_url,
            }
            previous = commands.get(command)
            if previous is None:
                commands[command] = command_evidence
            else:
                commands[command] = {
                    **command_evidence,
                    "conclusion": "ambiguous",
                    "job": f'{previous["job"]}, {job_name}',
                }

    return {"run": run, "jobs": jobs, "commands": commands}


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect GitHub Actions CI evidence")
    parser.add_argument("--needs-json", required=True, help="JSON-encoded Actions needs context")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument(
        "--timestamp",
        default=None,
        help="UTC timestamp; defaults to collection time",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    needs = json.loads(args.needs_json)
    if not isinstance(needs, dict):
        raise TypeError("Actions needs context must be a JSON object")
    timestamp = args.timestamp or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    results = build_ci_results(
        needs,
        run_id=args.run_id,
        commit=args.commit,
        timestamp=timestamp,
        run_url=args.run_url,
    )
    args.output.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Collected CI evidence in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
