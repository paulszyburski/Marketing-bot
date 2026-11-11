import os
import re
import sys
from datetime import datetime
from pathlib import Path


class YouTube:
    """Upload vertical videos through YouTube Studio using a saved session."""

    STUDIO_URL = "https://studio.youtube.com/?approve_browser_access=true&hl=en"

    def __init__(self, context, app):
        self.context = context
        self.app_name = app["appName"]
        self.timeout_ms = int(float(os.getenv("YOUTUBE_TIMEOUT_SECONDS", "120")) * 1000)
        self.publish_timeout_ms = int(
            float(os.getenv("YOUTUBE_PUBLISH_TIMEOUT_SECONDS", "300")) * 1000
        )
        context.set_default_timeout(self.timeout_ms)
        context.set_default_navigation_timeout(self.timeout_ms)
        self.page = context.new_page()

    def _studio_ready(self):
        return self.page.get_by_role(
            "button",
            name=re.compile(r"^(Create|Utwórz)$", re.I),
        ).first

    def _is_logged_out(self):
        return "accounts.google.com" in self.page.url

    def open(self):
        self.page.goto(self.STUDIO_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        if self._is_logged_out():
            self._wait_for_manual_login()
            self.page.goto(self.STUDIO_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        if self._is_logged_out():
            raise RuntimeError(f"YouTube login was not saved for {self.app_name}.")
        self._studio_ready().wait_for(state="visible", timeout=self.timeout_ms)
        print(f"Using the saved YouTube session for {self.app_name}.")

    def _wait_for_manual_login(self):
        message = (
            f"YouTube login is required for {self.app_name}. Complete the "
            "Google login in Chromium, then return here."
        )
        if not sys.stdin.isatty():
            raise RuntimeError(f"{message} Run the login helper from an interactive terminal first.")
        print(f"\n{message}")
        input("Press Enter after YouTube Studio has opened: ")

    def login_manually(self):
        self.page.goto(self.STUDIO_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        if not sys.stdin.isatty():
            raise RuntimeError("Manual YouTube login requires an interactive terminal.")
        print(f"\nLog in to YouTube for {self.app_name} in Chromium.")
        input("Press Enter after YouTube Studio has opened: ")

    def _click(self, locator):
        self._dismiss_survey()
        locator.wait_for(state="visible", timeout=self.timeout_ms)
        locator.click(timeout=self.timeout_ms)

    def _dismiss_survey(self):
        survey = self.page.locator("iframe#google-hats-survey")
        try:
            if not survey.is_visible(timeout=500):
                return
            no_thanks = self.page.frame_locator(
                "iframe#google-hats-survey"
            ).get_by_text(
                re.compile(r"^(No thanks|Nie, dziękuję)$", re.I),
                exact=True,
            )
            no_thanks.click(timeout=3000)
            print("Dismissed optional YouTube Studio survey")
        except Exception:
            # The survey is an optional cross-origin overlay. Removing its
            # iframe is safe and avoids it blocking upload-wizard controls.
            try:
                survey.evaluate("element => element.remove()")
                print("Removed optional YouTube Studio survey overlay")
            except Exception:
                pass

    def upload_video(self, video_path, description, hashtags):
        video_path = Path(video_path).expanduser().resolve()
        if not video_path.is_file():
            raise FileNotFoundError(f"Video not found: {video_path}")

        self._click(self._studio_ready())
        self._click(
            self.page.get_by_text(
                re.compile(r"^(Upload videos?|Prześlij filmy)$", re.I),
                exact=False,
            ).last
        )
        file_input = self.page.locator('input[type="file"]').last
        file_input.wait_for(state="attached", timeout=self.timeout_ms)
        file_input.set_input_files(str(video_path))

        dialog = self.page.locator(
            "ytcp-uploads-dialog tp-yt-paper-dialog#dialog"
        ).last
        dialog.wait_for(state="visible", timeout=self.timeout_ms)
        title_box = dialog.locator("#title-textarea #textbox").first
        title_box.wait_for(state="visible", timeout=self.timeout_ms)
        tags = " ".join(str(tag) for tag in hashtags)
        title_box.fill(f"{description.strip()} {tags}".strip()[:100])

        description_box = dialog.locator("#description-textarea #textbox").first
        if description_box.is_visible(timeout=3000):
            description_box.fill(f"{description.strip()}\n\n{tags}".strip())

        self._click(
            dialog.locator(
                'tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]'
            )
        )
        next_button = dialog.locator("#next-button button")
        for _ in range(3):
            self._click(next_button)
        self._click(
            dialog.locator('tp-yt-paper-radio-button[name="PUBLIC"]')
        )

        publish_button = dialog.locator("#done-button button")
        publish_button.wait_for(state="visible", timeout=self.timeout_ms)
        publish_button.click(timeout=self.publish_timeout_ms)

        # Studio may keep the upload wizard behind a separate processing
        # confirmation after publishing. The confirmation includes the
        # published video and a Close button, so it is also a success signal.
        processing_close = self.page.locator(
            "ytcp-uploads-still-processing-dialog #close-button button"
        ).last
        try:
            processing_close.wait_for(
                state="visible",
                timeout=15_000,
            )
            processing_close.click(timeout=self.timeout_ms)
        except Exception:
            # A successful Publish click is the hand-off to YouTube. Studio
            # does not consistently close its wizard or show the processing
            # confirmation, so neither is required as a second success signal.
            pass
        print(f"Published YouTube Short: {video_path.name}")

    def save_debug_artifacts(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data") / self.app_name / "browser_debug"
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = output_dir / f"youtube_failure_{timestamp}.png"
        html_path = output_dir / f"youtube_failure_{timestamp}.html"
        try:
            self.page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Saved YouTube failure screenshot: {screenshot_path}")
        except Exception as exc:
            print(f"Could not save YouTube failure screenshot: {exc}")
        try:
            html_path.write_text(self.page.content(), encoding="utf-8")
            print(f"Saved YouTube failure HTML: {html_path}")
        except Exception as exc:
            print(f"Could not save YouTube failure HTML: {exc}")
