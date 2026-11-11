from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

from automation.montage.branding import add_google_play_badge


def add_text_to_image(image, text):
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image)

    # Large, high-contrast short-form caption text.
    font_size = max(24, int(image.width * 0.058))

    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        size=font_size
    )

    # Don't let captions get too wide
    max_width = image.width * 0.72

    # -------------------------
    # WRAP TEXT
    # -------------------------

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()

        bbox = draw.textbbox((0, 0), test, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)

            current_line = word

    if current_line:
        lines.append(current_line)

    # -------------------------
    # SIZE EACH LINE
    # -------------------------

    line_gap = max(5, int(font_size * 0.18))

    line_data = []
    total_height = 0

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        line_data.append({
            "text": line,
            "bbox": bbox,
            "width": text_width,
            "height": text_height,
        })

        total_height += text_height

    total_height += line_gap * (len(lines) - 1)

    # -------------------------
    # CENTER WHOLE CAPTION
    # -------------------------

    center_x = image.width / 2
    current_y = (image.height - total_height) / 2

    for line in line_data:
        bbox = line["bbox"]
        text_x = center_x - line["width"] / 2 - bbox[0]
        text_y = current_y - bbox[1]

        draw.text(
            (text_x, text_y),
            line["text"],
            font=font,
            fill="black",
            stroke_width=max(3, int(font_size * 0.11)),
            stroke_fill="white",
        )

        current_y += line["height"] + line_gap

    return add_google_play_badge(image).convert("RGB")


def mend_text_and_image(image_url, text):
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()

    image = Image.open(BytesIO(response.content))
    return add_text_to_image(image, text)


def mend_texts_and_images(image_urls, texts):
    if len(image_urls) != len(texts):
        raise ValueError("image_urls and texts must have the same length")

    images = []

    for i, (image_url, text) in enumerate(zip(image_urls, texts), start=1):
        image = mend_text_and_image(image_url, text)
        images.append(image)

    return images
