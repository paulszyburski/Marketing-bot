from AI.videogeneration import generate_video
from AI.chatgpt import *
from montage.slides import *
from browser.pinterest import *

from datetime import date, datetime
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

            script = generate_video_script(
                video_idea,
                app
            )

            print(script)

            generate_video(script)

        break


def slides():
    apps = import_json(APPS_PATH)

    try:
        for app in apps:
            app_name = app["appName"]

            slides_idea = generate_slides_idea(app)

            slides_data = generate_slides(
                slides_idea,
                app
            )

            print(slides_data)

            texts = []
            image_urls = []

            for slide in slides_data["slides"]:
                text = slide["text"]
                image_query = slide["imageQuery"]

                print(f"\nSearching image for: {image_query}")

                image_url = search_image(
                    image_query,
                )

                if image_url is None:
                    print(
                        f"Skipping slide - no image found: "
                        f"{image_query}"
                    )
                    continue

                texts.append(text)
                image_urls.append(image_url)

            montaged_images = mend_texts_and_images(
                image_urls,
                texts,
            )

            print("Generated images:")
            print(montaged_images)

            print("Saving Images.")

            now = datetime.now()

            output_dir = f"data/{app_name}/slides/{now}"
            os.makedirs(output_dir, exist_ok=True)
            for i, image in enumerate(montaged_images):
                path = os.path.join(output_dir, f"image_{i}.jpg")

                image.save(path, quality=96)

            print("Saved!")

    finally:
        exit()


slides()