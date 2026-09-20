import json
from datetime import datetime
from pathlib import Path

from AI.chatgpt import generate_slides, generate_slides_idea
from browser.pinterest import search_image
from montage.slides import mend_texts_and_images


def find_slide_images(slides_data):
    texts = []
    image_urls = []

    for slide in slides_data["slides"]:
        image_query = slide["imageQuery"]
        print(f"\nSearching image for: {image_query}")

        image_url = search_image(image_query)
        if image_url is None:
            print(f"Skipping slide - no image found: {image_query}")
            continue

        texts.append(slide["text"])
        image_urls.append(image_url)

    return mend_texts_and_images(image_urls, texts)


def save_slideshow_data(app_name, slides_data):
    output_dir = Path("data") / app_name / "slides" / str(datetime.now().strftime("%Y.%m.%d_%H:%M"))
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(slides_data, f, indent=2, ensure_ascii=False)

    return output_dir


def save_slide_images(output_dir, images):
    for i, image in enumerate(images):
        image.save(output_dir / f"image_{i}.jpg", quality=96)


def generate_slideshow(app):
    slides_idea = generate_slides_idea(app)
    slides_data = generate_slides(slides_idea, app)
    print(slides_data)

    output_dir = save_slideshow_data(app["appName"], slides_data)
    images = find_slide_images(slides_data)
    save_slide_images(output_dir, images)

    print(f"Saved slideshow to {output_dir}")
    return str(output_dir)
