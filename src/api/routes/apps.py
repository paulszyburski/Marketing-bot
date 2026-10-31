from fastapi import APIRouter, HTTPException, status

from api.schemas.apps import AppEnabledUpdate, AppResponse
from api.services.apps import AppConfigurationError, get_app, list_apps, set_app_enabled


router = APIRouter()


@router.get("", response_model=list[AppResponse])
def get_apps(enabled_only: bool = False) -> list[AppResponse]:
    try:
        apps = list_apps(enabled_only=enabled_only)
    except AppConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return [AppResponse.from_config(app) for app in apps]


@router.patch("/{app_id}", response_model=AppResponse)
def update_app(app_id: str, update: AppEnabledUpdate) -> AppResponse:
    try:
        app = set_app_enabled(app_id, update.enabled)
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

    return AppResponse.from_config(app)


@router.get("/{app_id}", response_model=AppResponse)
def get_app_by_id(app_id: str) -> AppResponse:
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

    return AppResponse.from_config(app)
