#!/usr/bin/env python3
"""
voiceclone.py - clone your own voice from a short recording and speak any text with it.
Built for Intel Macs (CPU only), works on any platform.

  python voiceclone.py --check                                   # verify the install
  python voiceclone.py --ref me.m4a --text "Hello, it's me." --out hello.wav
  python voiceclone.py --ref me.m4a --text-file script.txt --out script.wav
  python voiceclone.py --ref me.m4a                              # interactive mode

Language is auto-detected (Arabic vs English); override with --lang.
Only clone voices you own or have permission to use.
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
ARABIC = re.compile(r"[\u0600-\u06FF]")
LANGS = ["en", "ar", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "zh-cn", "ja", "hu", "ko", "hi"]


def check_env() -> bool:
    ok = True
    print(f"Python {platform.python_version()} on {platform.system()} {platform.machine()}")
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        print("  ! Need Python 3.10-3.12 (3.11 recommended).")
        ok = False
    try:
        import numpy
        print(f"numpy {numpy.__version__}")
        if int(numpy.__version__.split(".")[0]) >= 2:
            print("  ! numpy 2.x breaks torch 2.2.2. Fix: pip install 'numpy<2'")
            ok = False
    except ImportError:
        print("  ! numpy missing"); ok = False
    try:
        import torch
        print(f"torch {torch.__version__} (cpu threads: {torch.get_num_threads()})")
    except ImportError:
        print("  ! torch missing"); ok = False
    try:
        import TTS  # noqa: F401
        print("coqui-tts OK")
    except ImportError:
        print("  ! coqui-tts missing"); ok = False
    conv = "ffmpeg" if shutil.which("ffmpeg") else ("afconvert (macOS built-in)" if shutil.which("afconvert") else None)
    print(f"audio converter: {conv or 'none - use .wav input'}")
    print("\nAll good." if ok else "\nFix the items marked ! above, then re-run --check.")
    return ok


def detect_lang(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    arabic = sum(1 for c in letters if ARABIC.match(c))
    return "ar" if arabic / len(letters) > 0.5 else "en"


def convert_to_wav(src: Path, dst: Path) -> Path:
    """Convert m4a/mp3/aiff/etc. to WAV using ffmpeg, or macOS's built-in afconvert."""
    if shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "22050", str(dst)]
    elif shutil.which("afconvert"):
        cmd = ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1", str(src), str(dst)]
    else:
        sys.exit("Can't convert this file type here. Provide a .wav file (or install ffmpeg).")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not dst.exists():
        sys.exit(f"Audio conversion failed:\n{(r.stderr or r.stdout)[-500:]}")
    return dst


def prepare_reference(src: Path, workdir: Path) -> Path:
    """Return a clean mono WAV: converted if needed, silence trimmed, capped at 30 seconds."""
    import numpy as np
    import soundfile as sf

    wav = src if src.suffix.lower() == ".wav" else convert_to_wav(src, workdir / "converted.wav")
    try:
        data, sr = sf.read(str(wav), always_2d=True)
    except Exception:
        wav = convert_to_wav(src, workdir / "converted.wav")  # odd WAV encodings
        data, sr = sf.read(str(wav), always_2d=True)

    mono = data.mean(axis=1)
    loud = np.where(np.abs(mono) > 0.01 * max(np.abs(mono).max(), 1e-9))[0]
    if len(loud):
        pad = int(0.1 * sr)
        mono = mono[max(loud[0] - pad, 0): loud[-1] + pad]
    mono = mono[: 30 * sr]

    secs = len(mono) / sr
    print(f"Reference: {secs:.1f}s of audio", end="")
    print("  (a bit short - 15-30s gives a better clone)" if secs < 8 else "")
    out = workdir / "reference.wav"
    sf.write(str(out), mono, sr)
    return out


def load_model():
    import torch
    from TTS.api import TTS

    torch.set_num_threads(os.cpu_count() or 2)
    device = "cuda" if torch.cuda.is_available() else "cpu"  # MPS is unreliable for XTTS, so Macs use CPU
    print(f"Loading model on {device} (first run downloads ~2 GB and asks you to accept the Coqui license)...")
    return TTS(MODEL).to(device)


def speak(tts, text: str, ref: Path, lang: str, out: Path, speed: float):
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tts.tts_to_file(text=text, speaker_wav=str(ref), language=lang,
                    file_path=str(out), speed=speed, split_sentences=True)
    print(f"Saved: {out}  ({time.time() - t0:.0f}s to generate)")


def main():
    p = argparse.ArgumentParser(description="Clone your voice and speak any text with it.")
    p.add_argument("--check", action="store_true", help="Verify the installation and exit.")
    p.add_argument("--ref", type=Path, help="Recording of your voice (wav/m4a/mp3/...). 15-30s of clean speech is ideal.")
    p.add_argument("--text", help="Text to speak.")
    p.add_argument("--text-file", type=Path, help="Read the text from a UTF-8 file.")
    p.add_argument("--lang", choices=LANGS, help="Language code. Default: auto-detect (ar/en).")
    p.add_argument("--out", type=Path, default=Path("output.wav"), help="Output WAV path.")
    p.add_argument("--speed", type=float, default=1.0, help="Speaking speed (0.9 slower, 1.1 faster).")
    args = p.parse_args()

    if args.check:
        sys.exit(0 if check_env() else 1)
    if not args.ref:
        p.error("--ref is required (or use --check)")
    if not args.ref.exists():
        sys.exit(f"Reference file not found: {args.ref}")

    text = args.text
    if args.text_file:
        text = args.text_file.read_text(encoding="utf-8").strip()

    with tempfile.TemporaryDirectory() as tmp:
        ref = prepare_reference(args.ref, Path(tmp))
        tts = load_model()

        if text:
            speak(tts, text, ref, args.lang or detect_lang(text), args.out, args.speed)
            return

        print("Interactive mode. Type text, press Enter. Empty line to quit.")
        n = 1
        while True:
            try:
                line = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                break
            speak(tts, line, ref, args.lang or detect_lang(line), Path(f"output_{n:03d}.wav"), args.speed)
            n += 1


if __name__ == "__main__":
    main()
