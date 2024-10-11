import io
import math
import os

import httpx

from mastodon.Mastodon import MediaAttachment
from PIL import Image, ImageDraw, ImageFont

from . import common

CELL_SIZE = 600
CELL_GAP = 10
NAME_POSITION = (0.5, 0.7)
FONT_PATH = os.getenv('FONT_PATH', common.DEFAULT_FONT_PATH)
FONT_SIZE = CELL_SIZE // 20
FONT_BACKGROUND = 'white'
FONT_COLOR = 'black'
FONT_GAP = 5


def generate_images(attachments: list[tuple[str, MediaAttachment]]):
    count = len(attachments)
    rows = math.ceil(count ** 0.5)
    cols = math.ceil(count / rows)

    canvas_width = cols * (CELL_SIZE + CELL_GAP) - CELL_GAP
    canvas_height = rows * (CELL_SIZE + CELL_GAP) - CELL_GAP

    question_canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    answer_canvas = question_canvas.copy()

    draw = ImageDraw.Draw(answer_canvas)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    for i, (acct, attachment) in enumerate(attachments):
        row = i // cols
        col = i % cols

        x = col * (CELL_SIZE + CELL_GAP)
        y = row * (CELL_SIZE + CELL_GAP)

        image = download_image(attachment)
        if not image:
            continue
        image = image.resize((CELL_SIZE, CELL_SIZE))

        question_canvas.paste(image, (x, y))
        answer_canvas.paste(image, (x, y))

        opts = {
            'xy': (x + CELL_SIZE * NAME_POSITION[0], y + CELL_SIZE * NAME_POSITION[1]),
            'text': acct,
            'font': font,
            'anchor': 'mm',
        }

        text_size = draw.textbbox(**opts)
        text_size = (
            text_size[0] - FONT_GAP,
            text_size[1] - FONT_GAP,
            text_size[2] + FONT_GAP,
            text_size[3] + FONT_GAP,
        )

        draw.rectangle(text_size, fill=FONT_BACKGROUND, outline=FONT_COLOR, width=2)

        draw.text(**opts, fill=FONT_COLOR)  # type: ignore

        question_canvas.save(common.QUESTION_IMAGE_PATH)
        answer_canvas.save(common.ANSWER_IMAGE_PATH)


def download_image(attachment: MediaAttachment) -> Image.Image | None:
    for url in [attachment.remote_url, attachment.url, attachment.preview_url]:
        if not url:
            continue

        try:
            response = httpx.get(url)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            return image
        except Exception:
            pass

    return None
