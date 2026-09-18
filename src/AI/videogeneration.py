import os
from pathlib import Path

import fal_client
from dotenv import load_dotenv


# Marketing-bot/.env
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

if not os.getenv("FAL_KEY"):
    raise ValueError(f"FAL_KEY not found in {ENV_PATH}")


MODEL = "fal-ai/kling-video/v3/turbo/standard/text-to-video"


def generate_video(prompt: str):

    handler = fal_client.submit(
        MODEL,
        arguments={
            "prompt": prompt,
            "resolution": "1080p",
            "aspect_ratio": "9:16",
        },
    )

    print("Request ID:", handler.request_id)

    for status in handler.iter_events(with_logs=True):
        print(status)

    result = handler.get()

    video_url = result["video"]["url"]

    print("Video URL:", video_url)

    return video_url