import json
import random
from datetime import datetime
from pathlib import Path

from PIL import Image

from automation.AI.chatgpt import generate_slides, generate_slides_idea
from automation.browser.pinterest import search_image
from automation.montage.slides import add_text_to_image, mend_text_and_image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTENT_STYLES = (
    "POV",
    "storytelling",
    "before and after",
    "tutorial",
    "comparison",
    "curiosity driven",
)


def find_proof_images(app):
    configured = app.get("proofAssetsPath")
    proof_dir = (
        Path(configured).expanduser()
        if configured
        else PROJECT_ROOT / "assets" / "proof" / str(app.get("id", app["appName"]))
    )
    if not proof_dir.is_absolute():
        proof_dir = PROJECT_ROOT / proof_dir
    proof_dir = proof_dir.resolve()

    if not proof_dir.is_dir():
        return proof_dir, []

    supported = {".jpg", ".jpeg", ".png", ".webp"}
    images = sorted(
        path for path in proof_dir.iterdir()
        if path.is_file() and path.suffix.lower() in supported
    )
    return proof_dir, images


def create_slide_images(slides_data, proof_dir):
    images = []
    for slide in slides_data["slides"]:
        if slide["imageSource"] == "proof":
            proof_path = (proof_dir / slide["proofImage"]).resolve()
            if proof_path.parent != proof_dir or not proof_path.is_file():
                raise ValueError(f"Invalid proof image: {slide['proofImage']}")
            with Image.open(proof_path) as proof_image:
                images.append(add_text_to_image(proof_image.copy(), slide["text"]))
            continue

        image_query = slide["imageQuery"]
        print(f"\nSearching image for: {image_query}")

        image_url = search_image(image_query)
        if image_url is None:
            raise RuntimeError(f"No image found for slide query: {image_query}")

        images.append(mend_text_and_image(image_url, slide["text"]))

    return images


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
    content_style = random.SystemRandom().choice(CONTENT_STYLES)
    proof_dir, proof_images = find_proof_images(app)
    proof_filenames = [path.name for path in proof_images]

    print(f"Content style: {content_style}")
    slides_idea = generate_slides_idea(app, content_style)
    slides_data = generate_slides(
        slides_idea,
        app,
        content_style,
        proof_filenames,
    )
    slides_data["contentStyle"] = content_style
    print(slides_data)

    output_dir = save_slideshow_data(app["appName"], slides_data)
    images = create_slide_images(slides_data, proof_dir)
    save_slide_images(output_dir, images)

    print(f"Saved slideshow to {output_dir}")
    return str(output_dir)
