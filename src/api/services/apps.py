import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_APPS_PATH = PROJECT_ROOT / "data" / "apps.json"
_apps_lock = threading.Lock()


class AppConfigurationError(RuntimeError):
    """Raised when the app configuration cannot be loaded."""


def _apps_path() -> Path:
    configured_path = os.getenv("APPS_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_APPS_PATH


def _load_apps() -> list[dict[str, Any]]:
    path = _apps_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AppConfigurationError(
            f"App configuration was not found at {path}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise AppConfigurationError(
            f"App configuration at {path} could not be read"
        ) from exc

    if not isinstance(data, list):
        raise AppConfigurationError("App configuration must contain a JSON list")

    return [app for app in data if isinstance(app, dict)]


def list_apps(enabled_only: bool = False) -> list[dict[str, Any]]:
    apps = _load_apps()
    if enabled_only:
        return [app for app in apps if app.get("enabled", True)]
    return apps


def get_app(app_id: str) -> dict[str, Any] | None:
    requested_id = app_id.casefold()
    return next(
        (
            app
            for app in _load_apps()
            if str(app.get("id", "")).casefold() == requested_id
        ),
        None,
    )


def set_app_enabled(app_id: str, enabled: bool) -> dict[str, Any] | None:
    """Persist an app's enabled state and return its updated configuration."""

    path = _apps_path()
    requested_id = app_id.casefold()

    with _apps_lock:
        apps = _load_apps()
        app = next(
            (
                item
                for item in apps
                if str(item.get("id", "")).casefold() == requested_id
            ),
            None,
        )
        if app is None:
            return None

        app["enabled"] = enabled
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                json.dump(apps, temporary_file, indent=2, ensure_ascii=False)
                temporary_file.write("\n")
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, path)
        except OSError as exc:
            if "temporary_path" in locals():
                temporary_path.unlink(missing_ok=True)
            raise AppConfigurationError(
                f"App configuration at {path} could not be updated"
            ) from exc

        return app
