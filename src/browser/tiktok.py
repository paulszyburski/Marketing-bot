import os
import re
import json
from pathlib import Path



class Tiktok:

    def __init__(self, context, app):
        self.app_name = app["appName"]
        self.context = context

        self.page = (context.pages[0] if context.pages else context.new_page())

        self.TIKTOK_EMAIL = os.getenv(f"{self.app_name.upper()}_TIKTOK_EMAIL")
        self.TIKTOK_PASSWORD = os.getenv(f"{self.app_name.upper()}_TIKTOK_PASSWORD")

    def open(self):
        self.page.goto("https://www.tiktok.com/")

    def add_music(self, music):
        if isinstance(music, str):
            title = music
            search_query = music
        else:
            title = music["title"]
            search_query = f'{title} {music["artist"]}'

        self.page.get_by_text(
            re.compile(r"^Add (sound|music)$", re.IGNORECASE)
        ).click()

        search_box = self.page.get_by_placeholder(
            re.compile("search", re.IGNORECASE)
        ).last
        search_box.fill(search_query)
        self.page.wait_for_timeout(1500)

        search_box.press("ArrowDown")
        search_box.press("Enter")
        self.page.wait_for_timeout(1500)

        self.page.get_by_role("button", name="Use", exact=True).first.click()

    def upload_video(self, video_path, description, hashtags):
        self.page.locator('button[aria-label="Upload"]').click()

        with self.page.expect_file_chooser() as file_info:
            self.page.get_by_text("Select video", exact=True).click()

        file_chooser = file_info.value
        file_chooser.set_files(video_path)

        caption_box = self.page.locator(
            'div[contenteditable="true"][role="combobox"]'
        ).first
        caption_box.click()

        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(description)
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Enter")

        for hashtag in hashtags:
            self.page.keyboard.type(hashtag)
            self.page.wait_for_timeout(1500)
            self.page.keyboard.press("Enter")

        self.page.locator('button[data-e2e="post_video_button"]').click()

    def upload_slides(self, slides_path, data):
        with open(data, "r", encoding="utf-8") as f:
            slides_data = json.load(f)

        photos = sorted(
            str(path.resolve())
            for path in Path(slides_path).iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )

        if not photos:
            raise ValueError(f"No photos found in {slides_path}")

        self.page.locator('button[aria-label="Upload"]').click()
        self.page.get_by_role("tab", name="Photos", exact=True).click()

        with self.page.expect_file_chooser() as file_info:
            self.page.get_by_text("Select photos", exact=True).click()

        file_chooser = file_info.value
        file_chooser.set_files(photos)

        self.add_music(slides_data["music"])

        caption_box = self.page.locator(
            'div[contenteditable="true"][role="combobox"]'
        ).first
        caption_box.click()

        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(slides_data["description"])
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Enter")

        for hashtag in slides_data["hashtags"]:
            self.page.keyboard.type(hashtag)
            self.page.wait_for_timeout(1500)
            self.page.keyboard.press("Enter")

        self.page.get_by_role("button", name="Post", exact=True).click()
