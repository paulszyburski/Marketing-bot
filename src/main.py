from AI.videogeneration import generate_video
from AI.chatgpt import *
from browser.tiktok import *
from browser.browser import *
from AI.slideshowgeneration import generate_slideshow
from montage.video import append_advertising_image
from playwright.sync_api import sync_playwright

import random
from pathlib import Path
from utils import *


APPS_PATH = "data/apps.json"


def _upload_with_browser(playwright, app, upload):
    chrome = Browser(app)
    pw_browser = None

    try:
        chrome.open()
        pw_browser = playwright.chromium.connect_over_cdp(chrome.cdp_url)
        context = pw_browser.contexts[0]
        tiktok = Tiktok(context, app)
        tiktok.open()
        upload(tiktok)
    finally:
        if pw_browser is not None:
            pw_browser.close()
        chrome.close()


def run_slideshow_pipeline(playwright, app):
    """Generate, assemble, and upload one complete slideshow post."""

    print(f"Creating a slideshow for {app['appName']}...")
    slides_path = generate_slideshow(app)
    slides_data = Path(slides_path) / "data.json"

    _upload_with_browser(
        playwright,
        app,
        lambda tiktok: tiktok.upload_slides(
            slides_path,
            str(slides_data),
        ),
    )


def run_video_pipeline(playwright, app):
    """Generate, montage, and upload one complete video post."""

    print(f"Creating a video for {app['appName']}...")
    video_idea = generate_video_idea(app)
    video_data = generate_video_script(video_idea, app)
    video_path = generate_video(video_data, app)

    _upload_with_browser(
        playwright,
        app,
        lambda tiktok: tiktok.upload_video(
            video_path,
            video_data["description"],
            video_data["hashtags"],
        ),
    )


def run_random_pipeline(playwright, app):
    """Upload a video 10% of the time and a slideshow 90% of the time."""

    if random.random() < 0.10:
        print("Random selection: video (10% chance)")
        return run_video_pipeline(playwright, app)

    print("Random selection: slideshow (90% chance)")
    return run_slideshow_pipeline(playwright, app)


def save_video_montage_preview(video_path, app):
    """Create a local montage preview without opening or uploading to TikTok."""

    advertising_image = app.get("advertisingImage")
    if not advertising_image:
        raise ValueError(
            f"No advertisingImage configured for {app['appName']}"
        )

    source_path = Path(video_path).expanduser().resolve()
    preview_dir = (
        Path("data")
        / app["appName"]
        / "montage_previews"
    )
    preview_path = preview_dir / f"{source_path.stem}_preview.mp4"

    result = append_advertising_image(
        source_path,
        advertising_image,
        output_path=preview_path,
    )
    print(f"Saved montage preview to {result}")
    return result


def test_video_montage():
    """Generate and montage a new video locally without uploading it."""

    apps = import_json(APPS_PATH)
    app = next(
        (candidate for candidate in apps if candidate.get("enabled", True)),
        None,
    )
    if app is None:
        raise ValueError("No enabled app found in data/apps.json")

    print(f"Generating a new video idea for {app['appName']}...")
    video_idea = generate_video_idea(app)
    print(video_idea)

    print("Generating the video script...")
    video_data = generate_video_script(video_idea, app)
    print(video_data)

    print("Generating the source video...")
    video_path = generate_video(video_data, app)
    print(f"Saved source video to {video_path}")

    preview_path = save_video_montage_preview(video_path, app)
    print("Test complete. Nothing was uploaded to TikTok.")

    return {
        "sourceVideo": video_path,
        "montagePreview": preview_path,
        "videoData": video_data,
    }


def main(apps):
    with sync_playwright() as p:
        for app in apps:
            if app.get("enabled", True):
                run_random_pipeline(p, app)

if __name__ == "__main__":
    apps = import_json(APPS_PATH)
    main(apps)
