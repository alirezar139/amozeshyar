# Regenerating the tour narration audio

The tour's narration in `frontend/public/audio/tour/*.wav` is pre-rendered,
not synthesized in the browser. If you edit `TOUR_STEPS` in
`frontend/composables/useGuide.ts` (change wording, add/remove a step, add
a new page's tour), regenerate the audio so it stays in sync — a step
without a matching `<route>-<index>.wav` file just won't play any audio.

**Why pre-rendered, and why via Docker specifically:** the tour text is
fixed, known ahead of time, so there's nothing to synthesize at runtime —
every visitor just plays a small static file, no client-side download or
ML inference. The generation itself needs `piper-tts==1.2.0` with the
classic `piper-phonemize` (espeak-ng) backend, because it's what these
community Piper voices were actually trained against; the newer
Windows-native `piper-tts` (1.8.0+, no `piper-phonemize` dependency)
produces garbled/looping Persian output, and `piper-phonemize` itself has
no Windows wheel at all — hence running the whole thing inside a
throwaway Linux container instead of natively.

## Steps

1. Extract the current step text:
   ```
   node scripts/extract-tour-text.mjs > tour-steps.json
   ```
2. Make sure the voice files exist locally (one-time download, ~60MB):
   ```
   curl -sL -o fa_IR-gyro-medium.onnx "https://huggingface.co/diffusionstudio/piper-voices/resolve/main/fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx"
   curl -sL -o fa_IR-gyro-medium.onnx.json "https://huggingface.co/diffusionstudio/piper-voices/resolve/main/fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx.json"
   ```
3. Run `generate-tour-audio.py` (loads the voice once via
   `piper.voice.PiperVoice`, sanitizes each step's text — strips ZWNJ,
   maps em/en dash to a Persian comma — and writes `<route>-<index>.wav`
   per step) inside a Linux container, e.g. on Windows with Git Bash:
   ```
   MSYS_NO_PATHCONV=1 docker run --rm \
     -v "<path-to-voices-dir>:/voices:ro" \
     -v "<repo>\scripts\generate-tour-audio.py:/generate.py:ro" \
     -v "<repo>\tour-steps.json:/data/tour-steps.json:ro" \
     -v "<repo>\frontend\public\audio\tour:/out" \
     python:3.11-slim bash -c "
       pip install --quiet 'onnxruntime<2,>=1.11.0' 'piper-phonemize~=1.1.0' piper-tts==1.2.0 &&
       python /generate.py
     "
   ```
   (On Windows/Git Bash, `MSYS_NO_PATHCONV=1` and Windows-style host paths
   in `-v` are required — plain `/c/...` paths silently fail to mount.)
