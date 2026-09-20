import os
import json
from pathlib import Path
from datetime import date

import fal_client
from dotenv import load_dotenv
from urllib.request import urlretrieve


# Marketing-bot/.env
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

MODEL = "fal-ai/kling-video/v3/turbo/standard/text-to-video"



def generate_video(video_data: dict, app: dict):
    if not os.getenv("FAL_KEY"):
        raise ValueError(f"FAL_KEY not found in {ENV_PATH}")

    handler = fal_client.submit(
        MODEL,
        arguments={
            "prompt": video_data["script"],
            "resolution": "1080p",
            "aspect_ratio": "9:16",
            "duration": "15",
        },
    )

    for status in handler.iter_events(with_logs=True):
        print(status)

    video_url = handler.get()["video"]["url"]

    folder = Path(f"data/{app["appName"]}/videos/{date.today()}")
    folder.mkdir(parents=True, exist_ok=True)

    i = len(list(folder.glob("video_*.mp4"))) + 1
    path = folder / f"video_{i}.mp4"

    urlretrieve(video_url, path)

    metadata_path = path.with_suffix(".json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(video_data, f, indent=2, ensure_ascii=False)

    return str(path)
