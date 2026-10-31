import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
LOG_PATH = PROJECT_ROOT / "data" / "logs" / "automation.log"
TIMER_UNIT = "marketing-bot.timer"
MAX_LOG_READ_BYTES = 256 * 1024

_lock = threading.Lock()
_process: subprocess.Popen[bytes] | None = None
_started_at: datetime | None = None
_finished_at: datetime | None = None


class AutomationAlreadyRunning(RuntimeError):
    """Raised when an automation run is already active."""


def _next_auto_run() -> datetime | None:
    """Read the next scheduled run from the user's systemd timer."""

    try:
        result = subprocess.run(
            [
                "systemctl",
                "list-timers",
                TIMER_UNIT,
                "--all",
                "--output=json",
                "--no-pager",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        timers = json.loads(result.stdout)
        next_timestamp = timers[0].get("next") if timers else None
        if not isinstance(next_timestamp, int) or next_timestamp <= 0:
            return None
        return datetime.fromtimestamp(next_timestamp / 1_000_000, timezone.utc)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, IndexError):
        return None


def _refresh_process() -> int | None:
    global _finished_at

    if _process is None:
        return None

    exit_code = _process.poll()
    if exit_code is not None and _finished_at is None:
        _finished_at = datetime.now(timezone.utc)
    return exit_code


def _run_state() -> dict[str, Any]:
    exit_code = _refresh_process()

    if _process is None:
        run_status = "idle"
    elif exit_code is None:
        run_status = "running"
    elif exit_code == 0:
        run_status = "succeeded"
    else:
        run_status = "failed"

    return {
        "status": run_status,
        "pid": _process.pid if _process is not None else None,
        "startedAt": _started_at,
        "finishedAt": _finished_at,
        "exitCode": exit_code,
        "logPath": str(LOG_PATH) if _process is not None else None,
        "nextAutoRunAt": _next_auto_run(),
    }


def start_run(
    app_id: str | None = None,
    pipeline: str = "random",
) -> dict[str, Any]:
    global _process, _started_at, _finished_at

    with _lock:
        if _process is not None and _refresh_process() is None:
            raise AutomationAlreadyRunning("The automation is already running")

        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        existing_python_path = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            f"{SRC_PATH}{os.pathsep}{existing_python_path}"
            if existing_python_path
            else str(SRC_PATH)
        )

        command = [sys.executable, "-m", "automation.main"]
        if app_id is not None:
            command.extend(["--app", app_id])
        command.extend(["--pipeline", pipeline])

        with LOG_PATH.open("ab") as log_file:
            started_label = datetime.now(timezone.utc).isoformat()
            target_label = app_id or "all enabled apps"
            log_file.write(
                f"\n=== Run started {started_label} · {target_label} "
                f"· {pipeline} pipeline ===\n".encode()
            )
            log_file.flush()
            _process = subprocess.Popen(
                command,
                cwd=PROJECT_ROOT,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        _started_at = datetime.now(timezone.utc)
        _finished_at = None
        return _run_state()


def get_run() -> dict[str, Any]:
    with _lock:
        return _run_state()


def get_logs(line_count: int = 200) -> dict[str, Any]:
    """Return a bounded tail of the automation log for the dashboard."""

    if not LOG_PATH.is_file():
        return {"lines": [], "truncated": False}

    with LOG_PATH.open("rb") as log_file:
        log_file.seek(0, os.SEEK_END)
        size = log_file.tell()
        offset = max(0, size - MAX_LOG_READ_BYTES)
        log_file.seek(offset)
        content = log_file.read().decode("utf-8", errors="replace")

    all_lines = content.splitlines()
    truncated = offset > 0 or len(all_lines) > line_count
    return {
        "lines": all_lines[-line_count:],
        "truncated": truncated,
    }
