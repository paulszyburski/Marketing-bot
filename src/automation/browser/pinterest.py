import os
import requests
import random


PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")


def search_image(query):
    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={
            "Authorization": PEXELS_API_KEY
        },
        params={
            "query": query,
            "orientation": "portrait",
            "size": "medium",
            "per_page": 10
        },
        timeout=20
    )

    response.raise_for_status()

    photos = response.json()["photos"]

    if not photos:
        return None

    # Could choose randomly from first few
    photo = random.choice(photos[:5])

    return photo["src"]["large2x"]