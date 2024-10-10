import os

DEFAULT_FONT_PATH = '/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf'

STORAGE_PATH = os.getenv('PICREW_STORAGE_PATH', 'state')
QUESTION_IMAGE_PATH = os.path.join(STORAGE_PATH, 'question.webp')
ANSWER_IMAGE_PATH = os.path.join(STORAGE_PATH, 'answer.webp')
STATE_PATH = os.path.join(STORAGE_PATH, 'state.json')

# Ensure directories exist
os.makedirs(STORAGE_PATH, exist_ok=True)
