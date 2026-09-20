from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import os


def mend_text_and_image(image_url, text):
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()

    image = Image.open(BytesIO(response.content)).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Much smaller, TikTok-like text
    font_size = max(18, int(image.width * 0.045))

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

    padding_x = max(8, int(font_size * 0.35))
    padding_y = max(4, int(font_size * 0.18))

    line_gap = max(2, int(font_size * 0.08))
    radius = max(5, int(font_size * 0.22))

    line_data = []
    total_height = 0

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        box_height = text_height + padding_y * 2

        line_data.append({
            "text": line,
            "bbox": bbox,
            "width": text_width,
            "height": text_height,
            "box_height": box_height
        })

        total_height += box_height

    total_height += line_gap * (len(lines) - 1)

    # -------------------------
    # CENTER WHOLE CAPTION
    # -------------------------

    center_x = image.width / 2
    current_y = (image.height - total_height) / 2

    for line in line_data:
        box_width = line["width"] + padding_x * 2
        box_height = line["box_height"]

        left = center_x - box_width / 2
        right = center_x + box_width / 2

        top = current_y
        bottom = current_y + box_height

        # White TikTok-style background
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=radius,
            fill="white"
        )

        bbox = line["bbox"]

        # Actual rendered text centered inside box
        text_x = center_x - line["width"] / 2 - bbox[0]

        text_y = (
            top
            + (box_height - line["height"]) / 2
            - bbox[1]
        )

        draw.text(
            (text_x, text_y),
            line["text"],
            font=font,
            fill="black"
        )

        current_y += box_height + line_gap

    return image


def mend_texts_and_images(image_urls, texts):
    if len(image_urls) != len(texts):
        raise ValueError("image_urls and texts must have the same length")

    images = []

    for i, (image_url, text) in enumerate(zip(image_urls, texts), start=1):
        image = mend_text_and_image(image_url, text)
        images.append(image)

    return images
