import io
import math
import os
import random

import httpx

from mastodon.return_types import MediaAttachment
from PIL import Image, ImageDraw, ImageFont

from . import common

CELL_SIZE = 600
CELL_GAP = 30
NAME_POSITION = (0.5, 0.8)
FONT_PATH = os.getenv('FONT_PATH', common.DEFAULT_FONT_PATH)
ANSWER_FONT_SIZE = CELL_SIZE // 20
NUMBER_FONT_SIZE = CELL_GAP
FONT_BACKGROUND = 'white'
FONT_COLOR = 'black'
FONT_GAP = 5


def generate_images(attachments: list[tuple[str, MediaAttachment]]):
    count = len(attachments)
    cols = math.ceil(count ** 0.5)
    rows = math.ceil(count / cols)

    random.shuffle(attachments)

    canvas_width = cols * (CELL_SIZE + CELL_GAP) + CELL_GAP
    canvas_height = rows * (CELL_SIZE + CELL_GAP) + CELL_GAP

    question_canvas = Image.new('RGBA', (canvas_width, canvas_height), 'white')
    answer_canvas = question_canvas.copy()

    question_draw = ImageDraw.Draw(question_canvas)
    answer_draw = ImageDraw.Draw(answer_canvas)
    answer_font = ImageFont.truetype(FONT_PATH, ANSWER_FONT_SIZE)
    number_font = ImageFont.truetype(FONT_PATH, NUMBER_FONT_SIZE)

    for i, (acct, attachment) in enumerate(attachments):
        row = i // cols
        col = i % cols
        number_caption = f'{i + 1:d}'

        x = col * (CELL_SIZE + CELL_GAP) + CELL_GAP
        y = row * (CELL_SIZE + CELL_GAP) + CELL_GAP

        image = download_image(attachment)
        if not image:
            continue

        # Convert to RGBA to handle transparency properly
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        image = image.resize((CELL_SIZE, CELL_SIZE))


        # Use alpha channel as mask for transparency
        question_canvas.paste(image, (x, y), image)
        answer_canvas.paste(image, (x, y), image)

        number_text_opts = {
            'xy': (x + CELL_SIZE / 2, y - CELL_GAP / 2),
            'text': number_caption,
            'font': number_font,
            'anchor': 'mm',
        }

        question_draw.text(**number_text_opts, fill=FONT_COLOR)  # type: ignore
        answer_draw.text(**number_text_opts, fill=FONT_COLOR)  # type: ignore

        answer_text_opts = {
            'xy': (x + CELL_SIZE * NAME_POSITION[0], y + CELL_SIZE * NAME_POSITION[1]),
            'text': acct,
            'font': answer_font,
            'anchor': 'mm',
        }

        text_size = answer_draw.textbbox(**answer_text_opts)
        box_size = (
            text_size[0] - FONT_GAP,
            text_size[1] - FONT_GAP,
            text_size[2] + FONT_GAP,
            text_size[3] + FONT_GAP,
        )

        answer_draw.rectangle(box_size, fill=FONT_BACKGROUND,
                              outline=FONT_COLOR, width=2)

        answer_draw.text(**answer_text_opts, fill=FONT_COLOR)  # type: ignore

    question_canvas = question_canvas.convert('RGB')
    answer_canvas = answer_canvas.convert('RGB')
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
