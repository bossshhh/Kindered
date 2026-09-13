"""Store assistant text and synthesize speech for playback."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _slug(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return digest


def synthesize_speech(text: str, voice_hint: str = "") -> dict:
    """
    Convert response text to a local audio file.
    Prefer macOS `say` when available; otherwise write a text sidecar and skip binary audio.
    """
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return {"audio_path": None, "audio_url": None, "status": "empty"}

    stem = _slug(clean + "|" + (voice_hint or ""))
    aiff_path = AUDIO_DIR / f"{stem}.aiff"
    wav_path = AUDIO_DIR / f"{stem}.wav"
    txt_path = AUDIO_DIR / f"{stem}.txt"
    txt_path.write_text(clean, encoding="utf-8")

    say_bin = shutil.which("say")
    if say_bin:
        cmd = [say_bin, "-o", str(aiff_path), clean]
        # Optional voice if user configured a macOS voice name.
        if voice_hint and voice_hint.lower() not in {"browser default", "browser default voice", ""}:
            cmd = [say_bin, "-v", voice_hint, "-o", str(aiff_path), clean]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            # Keep AIFF; browsers may not play it, so also try afconvert to wav when present.
            afconvert = shutil.which("afconvert")
            if afconvert:
                subprocess.run(
                    [afconvert, str(aiff_path), str(wav_path), "-f", "WAVE", "-d", "LEI16"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            playable = wav_path if wav_path.exists() else aiff_path
            return {
                "audio_path": str(playable),
                "audio_url": f"/api/audio/{playable.name}",
                "status": "ok",
                "engine": "macos_say",
            }
        except Exception as e:
            return {
                "audio_path": str(txt_path),
                "audio_url": None,
                "status": f"tts_failed:{type(e).__name__}",
                "engine": "none",
            }

    return {
        "audio_path": str(txt_path),
        "audio_url": None,
        "status": "no_tts_engine",
        "engine": "text_only",
    }
