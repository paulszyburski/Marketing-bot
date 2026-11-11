from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOOGLE_PLAY_BADGE = PROJECT_ROOT / "assets" / "branding" / "google-play-badge.png"


def _load_badge_master():
    if not GOOGLE_PLAY_BADGE.is_file():
        raise FileNotFoundError(f"Google Play badge not found: {GOOGLE_PLAY_BADGE}")
    with Image.open(GOOGLE_PLAY_BADGE) as source:
        source.seek(0)
        rgba = source.convert("RGBA")
        # Keep color and opacity as independent immutable masters. Resizing an
        # RGBA image repeatedly has produced corrupt color data with some
        # Pillow builds used on the automation server.
        return rgba.convert("RGB").copy(), rgba.getchannel("A").copy()


BADGE_COLOR_MASTER, BADGE_ALPHA_MASTER = _load_badge_master()


def add_google_play_badge(image, width_ratio=0.32, margin_ratio=0.03):
    """Place the official Google Play badge in the image's top-right corner."""
    canvas = image.convert("RGBA")
    badge_color = BADGE_COLOR_MASTER.copy()
    badge_alpha = BADGE_ALPHA_MASTER.copy()
    target_width = max(120, round(canvas.width * width_ratio))
    target_height = round(badge_color.height * target_width / badge_color.width)
    badge_color = badge_color.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    )
    badge_alpha = badge_alpha.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    )

    margin = max(12, round(canvas.width * margin_ratio))
    position = (canvas.width - badge_color.width - margin, margin)
    canvas.paste(badge_color, position, badge_alpha)
    return canvas


def create_google_play_overlay(path, width, height):
    """Save a transparent full-frame badge overlay for FFmpeg."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    add_google_play_badge(overlay).save(path)
