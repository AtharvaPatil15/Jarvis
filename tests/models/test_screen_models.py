import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from assistant.tools.builtin.screen import default_ocr, grab_primary_screen

pytestmark = pytest.mark.models


def test_ocr_reads_rendered_text() -> None:
    image = Image.new("RGB", (1200, 200), "white")
    ImageDraw.Draw(image).text((40, 60), "JARVIS SCREEN TEST 42", fill="black", font=ImageFont.truetype("arial.ttf", 64))
    bgr = np.asarray(image)[:, :, ::-1].copy()
    text = " ".join(default_ocr()(bgr)).upper()
    assert "JARVIS" in text and "42" in text


def test_real_screen_capture_returns_an_image() -> None:
    frame = grab_primary_screen()
    assert frame.ndim == 3 and frame.shape[2] == 3 and frame.shape[0] > 100
