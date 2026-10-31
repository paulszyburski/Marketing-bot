from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

import argparse
import os
import random
from pathlib import Path

from automation.pipelines.slideshow import run_slideshow_pipeline
from automation.pipelines.video import run_video_pipeline
from automation.utils import import_json, select_app_and_login


APPS_PATH = os.getenv("APPS_PATH", "data/apps.json")

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def login_manually():
    select_app_and_login(APPS_PATH)


def run_random_pipeline(playwright, app):
    if random.random() < 0.10:
        print("Random selection: video (10% chance)")
        return run_video_pipeline(playwright, app)

    print("Random selection: slideshow (90% chance)")
    return run_slideshow_pipeline(playwright, app)


def run_pipeline(playwright, app, pipeline):
    if pipeline == "video":
        print("Selected pipeline: video")
        return run_video_pipeline(playwright, app)
    if pipeline == "slideshow":
        print("Selected pipeline: slideshow")
        return run_slideshow_pipeline(playwright, app)
    return run_random_pipeline(playwright, app)


def parse_args():
    parser = argparse.ArgumentParser(description="Run the marketing automation")
    parser.add_argument(
        "--app",
        dest="app_id",
        help="Run the pipeline only for the app with this ID",
    )
    parser.add_argument(
        "--pipeline",
        choices=("random", "slideshow", "video"),
        default="random",
        help="Choose which pipeline to run (default: random)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    apps = import_json(APPS_PATH)

    if args.app_id:
        apps = [
            app
            for app in apps
            if str(app.get("id", "")).casefold() == args.app_id.casefold()
        ]
        if not apps:
            raise SystemExit(f"App '{args.app_id}' was not found")

    with sync_playwright() as p:
        for app in apps:
            if app.get("enabled", True):
                run_pipeline(p, app, args.pipeline)
