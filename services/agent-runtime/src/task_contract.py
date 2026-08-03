"""Immutable task-contract validation at the worker boundary."""

from __future__ import annotations

import fnmatch
import hashlib
import hmac
import json
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceLimitsContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maxRuntimeMinutes: int = Field(ge=1, le=1440)
    maxChangedFiles: int = Field(ge=1, le=1000)
    maxConcurrentAgents: int = Field(ge=1, le=16)
    networkAccess: Literal["denied", "allowlisted"]


class TaskExecutionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal["1"]
    projectId: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,128}$")
    taskId: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,128}$")
    objective: str = Field(min_length=1, max_length=20_000)
    capability: str | None = Field(default=None, max_length=128)
    contextRefs: list[str] = Field(default_factory=list, max_length=128)
    allowedPaths: list[str] = Field(min_length=1, max_length=128)
    requiredChecks: list[str] = Field(default_factory=list, max_length=32)
    limits: WorkspaceLimitsContract
    issuedAt: str

    def canonical_bytes(self) -> bytes:
        payload = self.model_dump(exclude_none=True)
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def assert_digest(self, expected: str) -> None:
        if not expected or not hmac.compare_digest(self.digest(), expected):
            raise ValueError("Task contract digest mismatch")

    def allows_path(self, raw_path: str) -> bool:
        normalized = raw_path.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts:
            return False
        candidate = path.as_posix()
        return any(
            pattern == "**" or fnmatch.fnmatchcase(candidate, pattern)
            for pattern in self.allowedPaths
        )
