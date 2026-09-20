import os
import re
import json
from pathlib import Path


class Tiktok:

    def __init__(self, context, app):
        self.app_name = app["appName"]
        self.context = context

        self.timeout_ms = int(
            float(os.getenv("TIKTOK_TIMEOUT_SECONDS", "90")) * 1000
        )
        self.settle_ms = int(
            float(os.getenv("TIKTOK_SETTLE_SECONDS", "5")) * 1000
        )

        context.set_default_timeout(self.timeout_ms)
        context.set_default_navigation_timeout(self.timeout_ms)

        self.page = (context.pages[0] if context.pages else context.new_page())

        self.TIKTOK_EMAIL = os.getenv(f"{self.app_name.upper()}_TIKTOK_EMAIL")
        self.TIKTOK_PASSWORD = os.getenv(f"{self.app_name.upper()}_TIKTOK_PASSWORD")

    def _click_when_ready(self, locator):
        locator.wait_for(state="visible", timeout=self.timeout_ms)
        locator.click(timeout=self.timeout_ms)

    def _upload_button(self):
        return self.page.locator('button[aria-label="Upload"]')

    def open(self):
        self.page.goto(
            "https://www.tiktok.com/",
            wait_until="domcontentloaded",
            timeout=self.timeout_ms,
        )
        self._upload_button().wait_for(
            state="visible",
            timeout=self.timeout_ms,
        )

    def add_music(self, music):
        if isinstance(music, str):
            title = music
            search_query = music
        else:
            title = music["title"]
            search_query = f'{title} {music["artist"]}'

        add_music_button = self.page.get_by_text(
            re.compile(r"^Add (sound|music)$", re.IGNORECASE)
        )
        self._click_when_ready(add_music_button)

        search_box = self.page.get_by_placeholder(
            re.compile("search", re.IGNORECASE)
        ).last
        search_box.wait_for(state="visible", timeout=self.timeout_ms)
        search_box.fill(search_query)
        self.page.wait_for_timeout(self.settle_ms)

        search_box.press("ArrowDown")
        search_box.press("Enter")
        self.page.wait_for_timeout(self.settle_ms)

        use_button = self.page.get_by_role(
            "button",
            name="Use",
            exact=True,
        ).first
        self._click_when_ready(use_button)
        self.page.wait_for_timeout(self.settle_ms)

    def upload_video(self, video_path, description, hashtags):
        self._click_when_ready(self._upload_button())

        select_video = self.page.get_by_text("Select video", exact=True)
        select_video.wait_for(state="visible", timeout=self.timeout_ms)
        with self.page.expect_file_chooser(timeout=self.timeout_ms) as file_info:
            select_video.click(timeout=self.timeout_ms)

        file_chooser = file_info.value
        file_chooser.set_files(video_path)
        self.page.wait_for_timeout(self.settle_ms)

        caption_box = self.page.locator(
            'div[contenteditable="true"][role="combobox"]'
        ).first
        self._click_when_ready(caption_box)

        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(description)
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Enter")

        for hashtag in hashtags:
            self.page.keyboard.type(hashtag)
            self.page.wait_for_timeout(self.settle_ms)
            self.page.keyboard.press("Enter")

        post_button = self.page.locator(
            'button[data-e2e="post_video_button"]'
        )
        self._click_when_ready(post_button)
        self.page.wait_for_timeout(self.settle_ms)

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

        self._click_when_ready(self._upload_button())

        photos_tab = self.page.get_by_role("tab", name="Photos", exact=True)
        self._click_when_ready(photos_tab)

        select_photos = self.page.get_by_text("Select photos", exact=True)
        select_photos.wait_for(state="visible", timeout=self.timeout_ms)
        with self.page.expect_file_chooser(timeout=self.timeout_ms) as file_info:
            select_photos.click(timeout=self.timeout_ms)

        file_chooser = file_info.value
        file_chooser.set_files(photos)
        self.page.wait_for_timeout(self.settle_ms)

        self.add_music(slides_data["music"])

        caption_box = self.page.locator(
            'div[contenteditable="true"][role="combobox"]'
        ).first
        self._click_when_ready(caption_box)

        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(slides_data["description"])
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Enter")

        for hashtag in slides_data["hashtags"]:
            self.page.keyboard.type(hashtag)
            self.page.wait_for_timeout(self.settle_ms)
            self.page.keyboard.press("Enter")

        post_button = self.page.get_by_role("button", name="Post", exact=True)
        self._click_when_ready(post_button)
        self.page.wait_for_timeout(self.settle_ms)
