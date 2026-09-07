"""Renders frontend/composables/useGuide.ts's TOUR_STEPS into WAV files.

Meant to run inside a Linux container (see generate-tour-audio.md for why
and the exact docker command) — expects /data/tour-steps.json (produced
by extract-tour-text.mjs), /voices/fa_IR-gyro-medium.onnx(.json), and
writes <route>-<index>.wav per step to /out.
"""

import json
import re
import wave
from pathlib import Path

from piper.voice import PiperVoice

STEPS = json.loads(Path("/data/tour-steps.json").read_text(encoding="utf-8"))
OUT_DIR = Path("/out")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize(text: str) -> str:
    # Mirrors the ZWNJ/dash handling the runtime code used to do for the
    # in-browser synthesizer — the espeak-ng phonemizer underneath Piper
    # stumbles on the invisible "نیم‌فاصله" character Persian compound
    # words use constantly, and doesn't treat an em/en dash as a pause.
    text = text.replace("‌", "")
    text = re.sub(r"[–—]", "،", text)
    return text


voice = PiperVoice.load("/voices/fa_IR-gyro-medium.onnx", "/voices/fa_IR-gyro-medium.onnx.json")

for step in STEPS:
    text = sanitize(f"{step['title']}. {step['text']}")
    out_path = OUT_DIR / f"{step['route']}-{step['index']}.wav"
    with wave.open(str(out_path), "wb") as wav_file:
        voice.synthesize(text, wav_file)
    print(f"wrote {out_path.name} ({out_path.stat().st_size} bytes)")

print(f"done: {len(STEPS)} files")
