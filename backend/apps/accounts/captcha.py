"""A custom, two-stage login captcha: drag-the-gem, then a distorted code.

Deliberately not a generic checkbox/text captcha. Stage 1 cuts a piece
from a site-themed gradient background in the shape of a diamond
(matching the "crystal" visual identity used everywhere else), and the
target position is never sent to the browser — only a rendered
background-with-socket image and a separate piece image. Stage 2 (only
reachable after stage 1 passes) shows a short digit code rendered as
hand-drawn seven-segment glyphs at random rotation over a noisy
background — no font file needed, and irregular enough to resist plain
OCR. Two different skills (drag-to-position, then read-and-type) in two
different rendering styles make this harder to script than either alone,
while staying fast and free (everything is generated locally with PIL).
"""

import base64
import secrets
from io import BytesIO
from random import Random

from django.core.cache import cache
from PIL import Image, ImageDraw, ImageFilter

CAPTCHA_WIDTH = 320
CAPTCHA_HEIGHT = 150
PIECE_SIZE = 46
TOLERANCE_PX = 8
CHALLENGE_TTL_SECONDS = 120
PASS_TTL_SECONDS = 120

NUMBER_WIDTH = 260
NUMBER_HEIGHT = 100
NUMBER_LENGTH = 5
NUMBER_TTL_SECONDS = 120

_PALETTES = [
    ((21, 126, 108), (6, 38, 31)),
    ((37, 99, 235), (23, 37, 84)),
    ((124, 58, 237), (46, 16, 101)),
    ((202, 138, 4), (113, 63, 18)),
]


def _gradient_background(rng: Random, w: int = CAPTCHA_WIDTH, h: int = CAPTCHA_HEIGHT) -> Image.Image:
    c1, c2 = rng.choice(_PALETTES)
    img = Image.new("RGB", (w, h), c1)
    top = Image.new("RGB", (w, h), c2)
    mask = Image.new("L", (w, h))
    mask.putdata([int(255 * ((x / w + y / h) / 2)) for y in range(h) for x in range(w)])
    img.paste(top, (0, 0), mask)
    return img.convert("RGBA")


def _diamond_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon([(size / 2, 0), (size, size / 2), (size / 2, size), (0, size / 2)], fill=255)
    return mask


def _to_data_url(img: Image.Image, fmt: str = "PNG") -> str:
    buf = BytesIO()
    img.save(buf, format=fmt)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/{fmt.lower()};base64,{encoded}"


def generate_challenge() -> dict:
    rng = Random()
    background = _gradient_background(rng)

    margin = 12
    target_x = rng.randint(PIECE_SIZE + margin, CAPTCHA_WIDTH - PIECE_SIZE - margin)
    target_y = rng.randint(margin, CAPTCHA_HEIGHT - PIECE_SIZE - margin)

    mask = _diamond_mask(PIECE_SIZE)

    # The piece: crop the gem shape out of the background at the secret
    # spot, with a bright rim so it reads as a distinct draggable object.
    piece = background.crop((target_x, target_y, target_x + PIECE_SIZE, target_y + PIECE_SIZE)).copy()
    piece.putalpha(mask)
    rim = Image.new("RGBA", piece.size, (0, 0, 0, 0))
    ImageDraw.Draw(rim).polygon(
        [(PIECE_SIZE / 2, 1), (PIECE_SIZE - 1, PIECE_SIZE / 2), (PIECE_SIZE / 2, PIECE_SIZE - 1), (1, PIECE_SIZE / 2)],
        outline=(255, 255, 255, 230),
        width=2,
    )
    piece = Image.alpha_composite(piece, rim)

    # The socket: darken the same diamond region directly on the background
    # so the user can see exactly where the piece belongs.
    socket_overlay = Image.new("RGBA", background.size, (0, 0, 0, 0))
    socket_overlay.paste((5, 8, 12, 210), (target_x, target_y), mask)
    background_with_socket = Image.alpha_composite(background, socket_overlay)
    background_with_socket = background_with_socket.filter(ImageFilter.SMOOTH)

    token = secrets.token_urlsafe(16)
    cache.set(f"captcha:{token}", {"x": target_x, "y": target_y}, CHALLENGE_TTL_SECONDS)

    return {
        "token": token,
        "background": _to_data_url(background_with_socket.convert("RGB"), "JPEG"),
        "piece": _to_data_url(piece, "PNG"),
        "piece_y": target_y,
        "width": CAPTCHA_WIDTH,
        "height": CAPTCHA_HEIGHT,
        "piece_size": PIECE_SIZE,
    }


# Seven-segment glyphs drawn with plain lines — no font file to bundle or
# keep in sync between dev/Docker/prod, and the blocky, slightly-rotated
# digits are already fairly OCR-resistant on their own before any noise
# is added on top.
_SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcfgd",
}


def _draw_seven_segment(rng: Random, digit: str, color: tuple[int, int, int]) -> Image.Image:
    w, h, t = 30, 54, 5
    canvas = Image.new("RGBA", (w + t * 2, h + t * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    x0, y0, x1, y1, xm, ym = t, t, t + w, t + h, t + w / 2, t + h / 2
    segment_lines = {
        "a": [(x0, y0), (x1, y0)],
        "b": [(x1, y0), (x1, ym)],
        "c": [(x1, ym), (x1, y1)],
        "d": [(x0, y1), (x1, y1)],
        "e": [(x0, ym), (x0, y1)],
        "f": [(x0, y0), (x0, ym)],
        "g": [(x0, ym), (x1, ym)],
    }
    for name in _SEGMENTS[digit]:
        draw.line(segment_lines[name], fill=color, width=t)
        for point in segment_lines[name]:
            draw.ellipse([point[0] - t / 2, point[1] - t / 2, point[0] + t / 2, point[1] + t / 2], fill=color)
    return canvas.rotate(rng.uniform(-14, 14), resample=Image.Resampling.BICUBIC, expand=True)


def generate_number_challenge() -> dict:
    rng = Random()
    code = "".join(str(rng.randint(0, 9)) for _ in range(NUMBER_LENGTH))
    # Drawn in plain RGB first — ImageDraw doesn't alpha-blend translucent
    # fills onto an RGBA image by default, it just overwrites the alpha
    # channel outright, which would make "faint" noise lines opaque. RGBA
    # is only needed afterwards, to alpha_composite the rotated digits.
    background = _gradient_background(rng, NUMBER_WIDTH, NUMBER_HEIGHT).convert("RGB")
    draw = ImageDraw.Draw(background)

    for _ in range(7):
        draw.line(
            [(rng.randint(0, NUMBER_WIDTH), rng.randint(0, NUMBER_HEIGHT)) for _ in range(2)],
            fill=(255, 255, 255),
            width=1,
        )
    for _ in range(40):
        x, y = rng.randint(0, NUMBER_WIDTH), rng.randint(0, NUMBER_HEIGHT)
        draw.ellipse([x, y, x + 2, y + 2], fill=(255, 255, 255))

    background = background.convert("RGBA")
    slot = NUMBER_WIDTH // NUMBER_LENGTH
    for i, digit in enumerate(code):
        glyph = _draw_seven_segment(rng, digit, (255, 255, 255))
        x = i * slot + (slot - glyph.width) // 2 + rng.randint(-4, 4)
        y = (NUMBER_HEIGHT - glyph.height) // 2 + rng.randint(-6, 6)
        background.alpha_composite(glyph, (x, y))

    token = secrets.token_urlsafe(16)
    cache.set(f"captcha_num:{token}", {"code": code}, NUMBER_TTL_SECONDS)

    return {
        "token": token,
        "image": _to_data_url(background.convert("RGB"), "JPEG"),
        "length": NUMBER_LENGTH,
    }


def verify_puzzle(token: str, achieved_x) -> dict | None:
    """Checks the drag against the secret target; one-shot (the challenge
    is consumed either way) so a single background/piece pair can't be
    replayed against repeated guesses. On success, hands back the stage-2
    (number) challenge directly rather than a pass — the puzzle alone was
    never meant to be sufficient."""
    data = cache.get(f"captcha:{token}")
    cache.delete(f"captcha:{token}")
    if not data:
        return None
    try:
        achieved_x = float(achieved_x)
    except (TypeError, ValueError):
        return None
    if abs(achieved_x - data["x"]) > TOLERANCE_PX:
        return None

    return generate_number_challenge()


def verify_number_and_issue_pass(token: str, submitted_code) -> str | None:
    """Checks the typed code against stage 2's secret; one-shot like stage
    1. Only this — the second, differently-shaped step — actually issues
    the pass LoginView requires."""
    data = cache.get(f"captcha_num:{token}")
    cache.delete(f"captcha_num:{token}")
    if not data or not isinstance(submitted_code, str):
        return None
    if submitted_code.strip() != data["code"]:
        return None

    pass_token = secrets.token_urlsafe(24)
    cache.set(f"captcha_pass:{pass_token}", True, PASS_TTL_SECONDS)
    return pass_token


def consume_pass(pass_token: str | None) -> bool:
    if not pass_token:
        return False
    key = f"captcha_pass:{pass_token}"
    if not cache.get(key):
        return False
    cache.delete(key)
    return True
