import json
import random
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

from automation.browser.browser import Browser
from automation.browser.tiktok import Tiktok
from automation.montage.video import append_advertising_image


def import_json(path):
    with open(path, "r") as f:
        data = json.load(f)

    return data


def upload_with_browser(playwright, app, upload):
    chrome = Browser(app)
    pw_browser = None

    try:
        chrome.open()
        pw_browser = playwright.chromium.connect_over_cdp(chrome.cdp_url)
        context = pw_browser.contexts[0]
        tiktok = Tiktok(context, app)
        tiktok.open()
        try:
            upload(tiktok)
        except Exception:
            tiktok.save_debug_artifacts()
            raise
    finally:
        if pw_browser is not None:
            pw_browser.close()
        chrome.close()


def choose_app(apps):
    """Prompt for one configured app and return it."""

    if not apps:
        raise ValueError("No apps found in data/apps.json")

    print("Choose an app to log in to:")
    for index, app in enumerate(apps, start=1):
        status = "" if app.get("enabled", True) else " (disabled)"
        print(f"  {index}. {app['appName']}{status}")

    while True:
        choice = input("App number: ").strip()
        try:
            selected_index = int(choice) - 1
            if selected_index < 0:
                raise IndexError
            return apps[selected_index]
        except (ValueError, IndexError):
            print(f"Enter a number between 1 and {len(apps)}.")


def select_app_and_login(apps_path):
    """Select an app and save its manually authenticated TikTok session."""

    apps = import_json(apps_path)
    app = choose_app(apps)

    with sync_playwright() as playwright:
        chrome = Browser(app)
        pw_browser = None
        try:
            chrome.open()
            pw_browser = playwright.chromium.connect_over_cdp(chrome.cdp_url)
            context = pw_browser.contexts[0]
            Tiktok(context, app).login_manually()
            print(
                f"Login session saved in {app['profilePath']} for "
                f"{app['appName']}."
            )
        finally:
            if pw_browser is not None:
                pw_browser.close()
            chrome.close()


def verify_tiktok_login(app):
    """Open TikTok with an app profile without starting an upload."""

    with sync_playwright() as playwright:
        chrome = Browser(app)
        pw_browser = None
        try:
            chrome.open()
            pw_browser = playwright.chromium.connect_over_cdp(chrome.cdp_url)
            context = pw_browser.contexts[0]
            Tiktok(context, app).open()
            print(
                f"TikTok login opened successfully for {app['appName']}. "
                "No upload was started."
            )
            input("Press Enter to close Chromium and finish the test: ")
        finally:
            if pw_browser is not None:
                pw_browser.close()
            chrome.close()


def run_test_pipeline(apps_path):
    """Generate a local post and verify login without uploading it."""

    from automation.AI.chatgpt import generate_video_idea, generate_video_script
    from automation.AI.slideshowgeneration import generate_slideshow
    from automation.AI.videogeneration import generate_video

    app = choose_app(import_json(apps_path))

    if random.random() < 0.10:
        print(f"Test selection: video for {app['appName']} (no upload)")
        video_idea = generate_video_idea(app)
        video_data = generate_video_script(video_idea, app)
        source_path = generate_video(video_data, app)
        preview_path = save_video_montage_preview(source_path, app)
        print(f"Dry run complete. Preview saved to {preview_path}")
        result = preview_path
    else:
        print(f"Test selection: slideshow for {app['appName']} (no upload)")
        slides_path = Path(generate_slideshow(app))
        advertising_image = Path(app["advertisingImage"]).expanduser().resolve()
        if not advertising_image.is_file():
            raise FileNotFoundError(
                f"Advertising image not found: {advertising_image}"
            )

        preview_ad = (
            slides_path / f"zz_advertisement{advertising_image.suffix}"
        )
        shutil.copy2(advertising_image, preview_ad)
        print(f"Dry run complete. Slideshow preview saved to {slides_path}")
        result = str(slides_path)

    print("Checking the saved TikTok login without uploading...")
    verify_tiktok_login(app)
    return result


def save_video_montage_preview(video_path, app):
    """Create a local montage preview without opening or uploading to TikTok."""

    advertising_image = app.get("advertisingImage")
    if not advertising_image:
        raise ValueError(f"No advertisingImage configured for {app['appName']}")

    source_path = Path(video_path).expanduser().resolve()
    preview_dir = Path("data") / app["appName"] / "montage_previews"
    preview_path = preview_dir / f"{source_path.stem}_preview.mp4"

    result = append_advertising_image(
        source_path,
        advertising_image,
        output_path=preview_path,
    )
    print(f"Saved montage preview to {result}")
    return result


def test_video_montage(apps_path="data/apps.json"):
    """Generate and montage a new video locally without uploading it."""

    # Imported here to keep the general utilities lightweight and avoid
    # loading the generation clients unless this test helper is called.
    from automation.AI.chatgpt import generate_video_idea, generate_video_script
    from automation.AI.videogeneration import generate_video

    apps = import_json(apps_path)
    app = next(
        (candidate for candidate in apps if candidate.get("enabled", True)),
        None,
    )
    if app is None:
        raise ValueError(f"No enabled app found in {apps_path}")

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
