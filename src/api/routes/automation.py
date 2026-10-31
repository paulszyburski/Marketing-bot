from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas.automation import AutomationLogResponse, AutomationRunResponse
from api.services.automation import (
    AutomationAlreadyRunning,
    get_logs,
    get_run,
    start_run,
)
from api.services.apps import AppConfigurationError, get_app


router = APIRouter()


@router.post(
    "/run",
    response_model=AutomationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_automation() -> AutomationRunResponse:
    """Start the complete automation pipeline in a separate process."""

    try:
        return AutomationRunResponse(**start_run())
    except AutomationAlreadyRunning as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/apps/{app_id}/run",
    response_model=AutomationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_app_automation(
    app_id: str,
    pipeline: Literal["random", "slideshow", "video"] = Query("random"),
) -> AutomationRunResponse:
    """Start the automation pipeline for one configured app."""

    try:
        app = get_app(app_id)
    except AppConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App '{app_id}' was not found",
        )
    if not app.get("enabled", True):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"App '{app_id}' is disabled",
        )

    try:
        return AutomationRunResponse(
            **start_run(app_id=str(app["id"]), pipeline=pipeline)
        )
    except AutomationAlreadyRunning as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/run", response_model=AutomationRunResponse)
def get_automation_run() -> AutomationRunResponse:
    """Return the state of the latest automation run."""

    return AutomationRunResponse(**get_run())


@router.get("/logs", response_model=AutomationLogResponse)
def get_automation_logs(lines: int = 200) -> AutomationLogResponse:
    """Return the latest lines written by website-triggered automation runs."""

    safe_line_count = min(max(lines, 20), 500)
    return AutomationLogResponse(**get_logs(safe_line_count))
