from pathlib import Path

from automation.AI.slideshowgeneration import generate_slideshow
from automation.utils import upload_with_browser


def run_slideshow_pipeline(playwright, app):
    print(f"Creating a slideshow for {app['appName']}...")
    slides_path = generate_slideshow(app)
    slides_data = Path(slides_path) / "data.json"

    upload_with_browser(
        playwright,
        app,
        lambda tiktok: tiktok.upload_slides(
            slides_path,
            str(slides_data),
        ),
    )
