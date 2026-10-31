from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AutomationRunResponse(BaseModel):
    status: Literal["idle", "running", "succeeded", "failed"]
    pid: int | None = None
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
    exitCode: int | None = None
    logPath: str | None = None
    nextAutoRunAt: datetime | None = None


class AutomationLogResponse(BaseModel):
    lines: list[str]
    truncated: bool = False
