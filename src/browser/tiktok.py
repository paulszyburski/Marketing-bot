import os
import re
import json
import sys
from pathlib import Path

from montage.video import append_advertising_image


class Tiktok:
    def __init__(self, context, app):
        self.app_name = app["appName"]
        advertising_image = app.get("advertisingImage")
        self.advertising_image = (
            Path(advertising_image).expanduser().resolve()
            if advertising_image
            else None
        )
        self.context = context

        self.timeout_ms = int(
            float(os.getenv("TIKTOK_TIMEOUT_SECONDS", "90")) * 1000
        )

        self.settle_ms = int(
            float(os.getenv("TIKTOK_SETTLE_SECONDS", "5")) * 1000
        )

        context.set_default_timeout(self.timeout_ms)
        context.set_default_navigation_timeout(self.timeout_ms)

        self.page = (
            context.pages[0]
            if context.pages
            else context.new_page()
        )

        self.TIKTOK_EMAIL = os.getenv(
            f"{self.app_name.upper()}_TIKTOK_EMAIL"
        )

        self.TIKTOK_PASSWORD = os.getenv(
            f"{self.app_name.upper()}_TIKTOK_PASSWORD"
        )

    def _click_when_ready(self, locator):
        locator.wait_for(
            state="visible",
            timeout=self.timeout_ms,
        )

        locator.click(
            timeout=self.timeout_ms,
        )

    def _upload_button(self):
        return self.page.locator(
            'button[aria-label="Upload"]'
        )

    def _advertising_image(self):
        if self.advertising_image is None:
            raise ValueError(
                f"No advertisingImage configured for {self.app_name}"
            )
        if not self.advertising_image.is_file():
            raise FileNotFoundError(
                f"Advertising image not found: {self.advertising_image}"
            )
        return self.advertising_image

    def _wait_for_upload_page(self):
        self.page.wait_for_url(
            re.compile(r"/tiktokstudio/upload(?:/|\?|$)"),
            timeout=self.timeout_ms,
        )

    def _wait_for_manual_login_if_needed(self):
        """Pause an interactive run while TikTok's login modal is open."""

        login_heading = self.page.get_by_text(
            re.compile(r"^Log in to TikTok$", re.IGNORECASE)
        ).last

        try:
            login_required = login_heading.is_visible(timeout=3000)
        except Exception:
            login_required = False

        if not login_required:
            return

        message = (
            "TikTok login is required. Complete the login in the Chromium "
            "window, then return here."
        )

        if not sys.stdin.isatty():
            raise RuntimeError(
                f"{message} Run src/main.py once from an interactive terminal "
                "so the browser profile can save the session."
            )

        print(f"\n{message}")
        input("Press Enter after the login window has closed: ")

        if login_heading.is_visible(timeout=1000):
            raise RuntimeError(
                "TikTok's login window is still open. Finish logging in "
                "before pressing Enter."
            )

    def _accept_cookies_if_present(self):
        """
        Accept TikTok cookies if a banner appears on the current page.
        If there is no cookie banner, continue normally.
        """

        button_name = re.compile(
            r"^(allow|accept) all(?: cookies)?$",
            re.IGNORECASE,
        )

        # The banner is normally in the main page, but checking every frame
        # also covers TikTok moving its consent UI into an iframe.
        for frame in self.page.frames:
            try:
                accept_button = frame.get_by_role(
                    "button",
                    name=button_name,
                ).last

                if not accept_button.is_visible(timeout=1000):
                    continue

                accept_button.click(timeout=5000)
                print("Accepted TikTok cookies")
                self.page.wait_for_timeout(1000)
                return True
            except Exception:
                continue

        return False

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

        self._wait_for_manual_login_if_needed()

    def add_music(self, music):
        if isinstance(music, str):
            title = music
            search_query = music

        else:
            title = music["title"]
            search_query = f'{title} {music["artist"]}'

        add_music_button = self.page.get_by_text(
            re.compile(
                r"^Add (sound|music)$",
                re.IGNORECASE,
            )
        )

        self._click_when_ready(
            add_music_button
        )

        search_box = self.page.get_by_placeholder(
            re.compile(
                "search",
                re.IGNORECASE,
            )
        ).last

        search_box.wait_for(
            state="visible",
            timeout=self.timeout_ms,
        )

        search_box.fill(
            search_query
        )

        self.page.wait_for_timeout(
            self.settle_ms
        )

        search_box.press(
            "ArrowDown"
        )

        search_box.press(
            "Enter"
        )

        self.page.wait_for_timeout(
            self.settle_ms
        )

        use_button = self.page.get_by_role(
            "button",
            name="Use",
            exact=True,
        ).first

        self._click_when_ready(
            use_button
        )

        self.page.wait_for_timeout(
            self.settle_ms
        )

    def upload_video(
        self,
        video_path,
        description,
        hashtags,
    ):
        video_path = append_advertising_image(
            video_path,
            self._advertising_image(),
        )

        self._wait_for_manual_login_if_needed()

        # Accept cookies if TikTok shows the banner
        self._accept_cookies_if_present()

        self._click_when_ready(
            self._upload_button()
        )

        # TikTok can show a fresh consent banner after navigating from the
        # home page to TikTok Studio.
        self._wait_for_upload_page()
        self._accept_cookies_if_present()

        select_video = self.page.get_by_text(
            "Select video",
            exact=True,
        )

        select_video.wait_for(
            state="visible",
            timeout=self.timeout_ms,
        )

        with self.page.expect_file_chooser(
            timeout=self.timeout_ms
        ) as file_info:

            select_video.click(
                timeout=self.timeout_ms
            )

        file_chooser = file_info.value

        file_chooser.set_files(
            video_path
        )

        self.page.wait_for_timeout(
            self.settle_ms
        )

        caption_box = self.page.locator(
            'div[contenteditable="true"][role="combobox"]'
        ).first

        self._click_when_ready(
            caption_box
        )

        self.page.keyboard.press(
            "Control+A"
        )

        self.page.keyboard.type(
            description
        )

        self.page.keyboard.press(
            "Enter"
        )

        self.page.keyboard.press(
            "Enter"
        )

        for hashtag in hashtags:
            self.page.keyboard.type(
                hashtag
            )

            self.page.wait_for_timeout(
                self.settle_ms
            )

            self.page.keyboard.press(
                "Enter"
            )

        post_button = self.page.locator(
            'button[data-e2e="post_video_button"]'
        )

        # Cookie banner could theoretically appear again
        self._accept_cookies_if_present()

        self._click_when_ready(
            post_button
        )

        self.page.wait_for_timeout(
            self.settle_ms
        )

    def upload_slides(
        self,
        slides_path,
        data,
    ):
        self._wait_for_manual_login_if_needed()

        # Accept cookies if TikTok shows the banner
        self._accept_cookies_if_present()

        with open(
            data,
            "r",
            encoding="utf-8",
        ) as f:
            slides_data = json.load(f)

        photos = sorted(
            str(path.resolve())
            for path in Path(slides_path).iterdir()
            if path.suffix.lower()
            in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
            }
        )

        if not photos:
            raise ValueError(
                f"No photos found in {slides_path}"
            )

        # Always upload the app-specific advertisement after every generated
        # slide, regardless of its filename.
        photos.append(str(self._advertising_image()))

        self._click_when_ready(
            self._upload_button()
        )

        # TikTok can show a fresh consent banner after navigating from the
        # home page to TikTok Studio.
        self._wait_for_upload_page()
        self._accept_cookies_if_present()

        photos_tab = self.page.get_by_role(
            "tab",
            name="Photos",
            exact=True,
        )

        self._click_when_ready(
            photos_tab
        )

        self._accept_cookies_if_present()

        select_photos = self.page.get_by_text(
            "Select photos",
            exact=True,
        )

        select_photos.wait_for(
            state="visible",
            timeout=self.timeout_ms,
        )

        with self.page.expect_file_chooser(
            timeout=self.timeout_ms
        ) as file_info:

            select_photos.click(
                timeout=self.timeout_ms
            )

        file_chooser = file_info.value

        file_chooser.set_files(
            photos
        )

        self.page.wait_for_timeout(
            self.settle_ms
        )

        self.add_music(
            slides_data["music"]
        )

        caption_box = self.page.locator(
            'div[contenteditable="true"][role="combobox"]'
        ).first

        self._click_when_ready(
            caption_box
        )

        self.page.keyboard.press(
            "Control+A"
        )

        self.page.keyboard.type(
            slides_data["description"]
        )

        self.page.keyboard.press(
            "Enter"
        )

        self.page.keyboard.press(
            "Enter"
        )

        for hashtag in slides_data["hashtags"]:
            self.page.keyboard.type(
                hashtag
            )

            self.page.wait_for_timeout(
                self.settle_ms
            )

            self.page.keyboard.press(
                "Enter"
            )

        post_button = self.page.get_by_role(
            "button",
            name="Post",
            exact=True,
        )

        # Check again immediately before Post
        self._accept_cookies_if_present()

        self._click_when_ready(
            post_button
        )

        self.page.wait_for_timeout(
            self.settle_ms
        )
