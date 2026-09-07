"""A custom "drag the gem into its socket" login captcha.

Deliberately not a generic checkbox/text captcha: the piece is cut from a
site-themed gradient background in the shape of a diamond (matching the
"crystal" visual identity used everywhere else), and the target position
is never sent to the browser — only a rendered background-with-socket
image and a separate piece image. The frontend just lets a human *see*
where the socket is and drag to it; the server is the only party that
ever knows the correct x, so a bot can't just read it off the response
and submit a perfect answer without actually solving the visual puzzle.
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

_PALETTES = [
    ((21, 126, 108), (6, 38, 31)),
    ((37, 99, 235), (23, 37, 84)),
    ((124, 58, 237), (46, 16, 101)),
    ((202, 138, 4), (113, 63, 18)),
]


def _gradient_background(rng: Random) -> Image.Image:
    c1, c2 = rng.choice(_PALETTES)
    w, h = CAPTCHA_WIDTH, CAPTCHA_HEIGHT
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


def verify_and_issue_pass(token: str, achieved_x) -> str | None:
    """Checks the drag against the secret target; one-shot (the challenge
    is consumed either way) so a single background/piece pair can't be
    replayed against repeated guesses."""
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
