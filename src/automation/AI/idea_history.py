import json
from datetime import datetime, timezone
from pathlib import Path


MAX_SAVED_IDEAS = 50
MAX_PROMPT_IDEAS = 20


def _history_path(app: dict) -> Path:
    return Path("data") / app["appName"] / "idea_history.json"


def load_idea_history(app: dict) -> list[dict]:
    path = _history_path(app)
    if not path.exists():
        return []

    try:
        history = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(history, list):
        return []

    return [entry for entry in history if isinstance(entry, dict)]


def recent_ideas(app: dict, limit: int = MAX_PROMPT_IDEAS) -> list[dict]:
    return load_idea_history(app)[-limit:]


def remember_idea(app: dict, content_type: str, idea: str) -> None:
    path = _history_path(app)
    path.parent.mkdir(parents=True, exist_ok=True)

    history = load_idea_history(app)
    history.append(
        {
            "contentType": content_type,
            "idea": idea.strip(),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    history = history[-MAX_SAVED_IDEAS:]

    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)
