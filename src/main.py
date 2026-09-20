from AI.videogeneration import generate_video
from AI.chatgpt import *
from browser.tiktok import *
from browser.browser import *
from AI.slideshowgeneration import generate_slideshow
from playwright.sync_api import sync_playwright

import time
from datetime import date
from pathlib import Path
from utils import *


last_day = date.today()

APPS_PATH = "data/apps.json"


def videos():
    while True:
        today = date.today()

        if today == last_day:
            pass

        apps = import_json(APPS_PATH)

        for app in apps:
            video_idea = generate_video_idea(app)

            print(video_idea, "\n\n\n\n\n")

            video_data = generate_video_script(
                video_idea,
                app
            )

            print(video_data)

            generate_video(video_data, app)

        break


def slides():
    for app in import_json(APPS_PATH):
        generate_slideshow(app)


def open_tiktok(apps):

    with sync_playwright() as p:

        for app in apps:
            chrome = Browser(app)
            chrome.open()

            pw_browser = p.chromium.connect_over_cdp(chrome.cdp_url)

            context = pw_browser.contexts[0]

            tiktok = Tiktok(context, app)

            tiktok.open()

            time.sleep(10)

            video_path = "data/DriveProof/videos/2026-09-19/video_3.mp4"
            video_data = import_json(Path(video_path).with_suffix(".json"))

            slides_path = "data/DriveProof/slides/2026.09.19_18:42"
            slides_data = "data/DriveProof/slides/2026.09.19_18:42/data.json"

            #tiktok.upload_video(video_path,video_data["description"],video_data["hashtags"],)
            tiktok.upload_slides(slides_path, slides_data)

            # do TikTok stuff here
            # tiktok.upload(...)
            # tiktok.post(...)
            input()

            pw_browser.close()
            chrome.close()

def main(apps):
    with sync_playwright() as p:
        for app in apps:
            chrome = Browser(app)
            pw_browser = None

            try:
                chrome.open()
                pw_browser = p.chromium.connect_over_cdp(chrome.cdp_url)
                context = pw_browser.contexts[0]
                tiktok = Tiktok(context, app)

                slides_path = generate_slideshow(app)
                slides_data = Path(slides_path) / "data.json"

                tiktok.open()
                tiktok.upload_slides(slides_path, str(slides_data))
            finally:
                if pw_browser is not None:
                    pw_browser.close()
                chrome.close()

if __name__ == "__main__":
    apps = import_json(APPS_PATH)
    main(apps)
