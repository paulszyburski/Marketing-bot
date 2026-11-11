import json
from pathlib import Path

from automation.AI.slideshowgeneration import generate_slideshow
from automation.montage.slideshow_video import render_slideshow_video
from automation.utils import upload_to_socials


def run_slideshow_pipeline(playwright, app):
    print(f"Creating a slideshow for {app['appName']}...")
    slides_path = generate_slideshow(app)
    slides_data = Path(slides_path) / "data.json"
    data = json.loads(slides_data.read_text(encoding="utf-8"))
    youtube_video = render_slideshow_video(
        slides_path,
        app["advertisingImage"],
        background_music=app.get("backgroundMusic"),
    )

    upload_to_socials(
        playwright,
        app,
        lambda tiktok: tiktok.upload_slides(
            slides_path,
            str(slides_data),
        ),
        lambda youtube: youtube.upload_video(
            youtube_video,
            data["description"],
            data["hashtags"],
        ),
    )
