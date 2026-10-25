import json
from datetime import datetime, timezone
from pathlib import Path


MAX_SAVED_AUDIO = 100
MAX_PROMPT_AUDIO = 50


def _history_path(app: dict) -> Path:
    return Path("data") / app["appName"] / "audio_history.json"


def _audio_key(title: str, artist: str) -> tuple[str, str]:
    return (title.strip().casefold(), artist.strip().casefold())


def load_audio_history(app: dict) -> list[dict]:
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


def recent_audio(app: dict, limit: int = MAX_PROMPT_AUDIO) -> list[dict]:
    return load_audio_history(app)[-limit:]


def audio_was_used(app: dict, title: str, artist: str) -> bool:
    requested_audio = _audio_key(title, artist)
    return any(
        _audio_key(str(entry.get("title", "")), str(entry.get("artist", "")))
        == requested_audio
        for entry in load_audio_history(app)
    )


def remember_audio(app: dict, title: str, artist: str) -> None:
    title = title.strip()
    artist = artist.strip()
    path = _history_path(app)
    path.parent.mkdir(parents=True, exist_ok=True)

    history = load_audio_history(app)
    if any(
        _audio_key(str(entry.get("title", "")), str(entry.get("artist", "")))
        == _audio_key(title, artist)
        for entry in history
    ):
        return

    history.append(
        {
            "title": title,
            "artist": artist,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    history = history[-MAX_SAVED_AUDIO:]

    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)
