import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path

from automation.montage.video import append_advertising_image
from automation.montage.branding import add_google_play_badge
from PIL import Image


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

        # Prefer the stable app id for environment-variable names.  Falling
        # back to appName keeps older app definitions working.  Non-alphanumeric
        # characters are converted to underscores so the result is a valid
        # shell variable name (for example, "My App" becomes "MY_APP").
        credential_name = app.get("id") or self.app_name
        credential_prefix = re.sub(
            r"[^A-Z0-9]+",
            "_",
            credential_name.upper(),
        ).strip("_")

        self.TIKTOK_EMAIL = os.getenv(f"{credential_prefix}_EMAIL")
        self.TIKTOK_PASSWORD = os.getenv(f"{credential_prefix}_PASSWORD")

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

    def _visible_dialog(self):
        dialogs = self.page.locator('[role="dialog"]')
        for index in range(dialogs.count() - 1, -1, -1):
            dialog = dialogs.nth(index)
            try:
                if dialog.is_visible(timeout=500):
                    return dialog
            except Exception:
                continue
        return None

    def _clear_upload_dialog(self):
        """Wait for processing dialogs and close safe leftover upload modals."""

        dialog = self._visible_dialog()
        if dialog is None:
            return

        try:
            dialog_text = " ".join(dialog.inner_text(timeout=3000).split())
        except Exception:
            dialog_text = "<dialog text unavailable>"
        print(f"TikTok blocking dialog: {dialog_text[:500]}")

        # This optional account-setting prompt appears after a successful file
        # selection. Decline it so the upload can continue without changing the
        # user's automatic content-check preference.
        if re.search(r"turn on automatic content checks", dialog_text, re.I):
            cancel_button = dialog.get_by_role(
                "button",
                name=re.compile(r"^cancel$", re.I),
            ).last
            cancel_button.click(timeout=5000)
            dialog.wait_for(state="hidden", timeout=10000)
            print("Declined optional automatic content checks")
            return

        # Processing dialogs should finish by themselves. Give video processing
        # longer than the normal element timeout before attempting recovery.
        if re.search(r"uploading|processing|checking|preparing", dialog_text, re.I):
            try:
                dialog.wait_for(state="hidden", timeout=max(self.timeout_ms, 180_000))
                print("TikTok upload-processing dialog closed")
                return
            except Exception:
                pass

        safe_button = dialog.get_by_role(
            "button",
            name=re.compile(r"^(close|done|got it|not now|continue)$", re.I),
        ).last
        try:
            if safe_button.is_visible(timeout=1500):
                safe_button.click(timeout=5000)
                dialog.wait_for(state="hidden", timeout=10000)
                print("Closed TikTok blocking dialog")
                return
        except Exception:
            pass

        # TikTok's upload-choice modal is dismissible with Escape after the
        # selected file has already been handed to the browser.
        self.page.keyboard.press("Escape")
        try:
            dialog.wait_for(state="hidden", timeout=10000)
            print("Dismissed TikTok blocking dialog with Escape")
            return
        except Exception as exc:
            raise RuntimeError(
                f"TikTok dialog still blocks the upload form: {dialog_text[:500]}"
            ) from exc

    def _dismiss_tutorial_overlay(self):
        overlay = self.page.locator('[data-test-id="overlay"]').last
        try:
            if not overlay.is_visible(timeout=1500):
                return False
        except Exception:
            return False

        got_it = self.page.get_by_role(
            "button",
            name=re.compile(r"^got it$", re.I),
        ).last
        got_it.click(timeout=5000)
        overlay.wait_for(state="hidden", timeout=10000)
        print("Dismissed TikTok editing-features tutorial")
        return True

    def save_debug_artifacts(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data") / self.app_name / "browser_debug"
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = output_dir / f"failure_{timestamp}.png"
        html_path = output_dir / f"failure_{timestamp}.html"

        try:
            self.page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Saved browser failure screenshot: {screenshot_path}")
        except Exception as exc:
            print(f"Could not save browser failure screenshot: {exc}")
        try:
            html_path.write_text(self.page.content(), encoding="utf-8")
            print(f"Saved browser failure HTML: {html_path}")
        except Exception as exc:
            print(f"Could not save browser failure HTML: {exc}")

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
                f"{message} Run automation.main from an interactive terminal "
                "so the browser profile can save the session."
            )

        print(f"\n{message}")
        input("Press Enter after the login window has closed: ")

        if login_heading.is_visible(timeout=1000):
            raise RuntimeError(
                "TikTok's login window is still open. Finish logging in "
                "before pressing Enter."
            )

    def _is_logged_out(self):
        login_button = self.page.locator(
            '[data-e2e="top-login-button"]'
        ).first
        try:
            return (
                login_button.is_visible(timeout=3000)
                or "/login" in self.page.url
            )
        except Exception:
            return "/login" in self.page.url

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

        self._accept_cookies_if_present()

        if self._is_logged_out():
            print(
                f"The saved browser profile for {self.app_name} is not "
                "logged in yet."
            )
            self.login_manually()
            self.page.goto(
                "https://www.tiktok.com/",
                wait_until="domcontentloaded",
                timeout=self.timeout_ms,
            )
            if self._is_logged_out():
                raise RuntimeError(
                    f"TikTok login was not saved for {self.app_name}."
                )
        else:
            print(
                f"Using the saved TikTok session for {self.app_name}."
            )

        self._upload_button().wait_for(
            state="visible",
            timeout=self.timeout_ms,
        )

    def login_manually(self):
        """Open TikTok and keep Chromium running until login is complete."""

        self.page.goto(
            "https://www.tiktok.com/login",
            wait_until="domcontentloaded",
            timeout=self.timeout_ms,
        )
        self._accept_cookies_if_present()

        if not sys.stdin.isatty():
            raise RuntimeError(
                "Manual login requires an interactive terminal."
            )

        print(
            f"\nLog in to TikTok for {self.app_name} in the Chromium window."
        )
        if self.TIKTOK_EMAIL:
            print(f"Configured email: {self.TIKTOK_EMAIL}")
        else:
            print(
                "No app email is configured; enter the account details "
                "directly in Chromium."
            )
        input("Press Enter here after login is complete: ")

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
        source_path = Path(video_path)
        text_overlays = None
        metadata_path = source_path.with_suffix(".json")
        if metadata_path.is_file():
            try:
                video_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                text_overlays = [
                    (video_metadata.get("hookText"), 0.0, 2.8),
                    (video_metadata.get("benefitText"), 6.0, 10.5),
                ]
            except (OSError, json.JSONDecodeError):
                text_overlays = None

        if source_path.stem.endswith("_with_ad"):
            video_path = str(source_path.resolve())
        else:
            video_path = append_advertising_image(
                video_path,
                self._advertising_image(),
                text_overlays=text_overlays,
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
        self._clear_upload_dialog()
        self._dismiss_tutorial_overlay()

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
            if not path.name.startswith(".") and path.suffix.lower()
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
        badged_advertising_image = Path(slides_path) / ".tiktok_ad_with_badge.png"
        with Image.open(self._advertising_image()) as ad_image:
            add_google_play_badge(ad_image).save(badged_advertising_image)
        photos.append(str(badged_advertising_image.resolve()))

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

        try:
            file_chooser.set_files(photos)
        finally:
            badged_advertising_image.unlink(missing_ok=True)

        self.page.wait_for_timeout(
            self.settle_ms
        )

        self.add_music(
            slides_data["music"]
        )

        self._clear_upload_dialog()
        self._dismiss_tutorial_overlay()

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
