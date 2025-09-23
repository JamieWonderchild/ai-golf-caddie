from __future__ import annotations

import os
import json
from typing import Optional

import httpx
import socket
from urllib.parse import urlparse
import numpy as np
import wave
import sys
import tempfile

try:
    import sounddevice as sd  # type: ignore
except Exception as _e:  # pragma: no cover
    sd = None


def speak(
    text: str,
    *,
    language: str = "en",
    voice: Optional[str] = None,
    sample_rate: int = 16000,
) -> None:
    """Speak text using Speechmatics TTS preview API.

    Per the quickstart, the endpoint returns raw PCM float32 (little-endian) at 16 kHz mono.

    Env vars:
      - SPEECHMATICS_API_KEY (required)
      - SPEECHMATICS_TTS_URL (optional; defaults to preview endpoint)
    Reference: https://docs.speechmatics.com/text-to-speech/quickstart
    """
    api_key = os.getenv("SPEECHMATICS_API_KEY")
    if not api_key:
        print("Speechmatics TTS: SPEECHMATICS_API_KEY not set; printing text instead:")
        print(text)
        return

    tts_url = os.getenv("SPEECHMATICS_TTS_URL", "https://preview.tts.speechmatics.com/generate")
    # Debug: show config
    if os.getenv("GC_DEBUG"):
        print(f"[TTS] using url={tts_url} text_len={len(text)} api_key_set={bool(api_key)}")
    # DNS debug
    try:
        host = urlparse(tts_url).hostname
        if host:
            try:
                addrs = socket.getaddrinfo(host, None)
                if os.getenv("GC_DEBUG"):
                    print(f"[TTS] DNS {host} -> {set(a[4][0] for a in addrs)}")
            except Exception as dns_err:
                fallback = "https://preview.tts.speechmatics.com/generate"
                if os.getenv("GC_DEBUG"):
                    print(f"[TTS] DNS failed for {host}: {dns_err}. Falling back to {fallback}")
                tts_url = fallback
    except Exception as e:
        print(f"[TTS] DNS lookup failed: {e}")

    payload = {"text": text}
    # language/voice selection may be added by the service later; keep payload minimal per quickstart

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(tts_url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()

            # Quickstart says: raw PCM float32 little-endian at 16 kHz mono
            raw_audio = resp.content
            if os.getenv("GC_DEBUG"):
                print(f"[TTS] HTTP {resp.status_code} content-type={resp.headers.get('content-type')} bytes={len(raw_audio)}")
            if sd is None:  # pragma: no cover
                print("Speechmatics TTS: sounddevice not available; printing text:")
                print(text)
                return

            float_samples = np.frombuffer(raw_audio, dtype='<f4')
            # Debug: short confirmation of playback parameters
            print(f"[TTS] url={tts_url} bytes={len(raw_audio)} samples={len(float_samples)} sr={sample_rate}")

            # Only save WAV if replay is requested; otherwise avoid leaving files around
            wav_path = None
            want_replay = bool(os.getenv("GC_TTS_REPLAY"))
            if want_replay:
                try:
                    int16_samples = (np.clip(float_samples, -1.0, 1.0) * 32767).astype(np.int16)
                    fd, tmp_path = tempfile.mkstemp(prefix="golfcaddie_tts_", suffix=".wav")
                    os.close(fd)
                    with wave.open(tmp_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(sample_rate)
                        wf.writeframes(int16_samples.tobytes())
                    wav_path = tmp_path
                    if os.getenv("GC_DEBUG"):
                        print(f"[TTS] Saved WAV for replay: {wav_path}")
                except Exception as wav_err:
                    print(f"[TTS] Could not save WAV for replay: {wav_err}")

            # Attempt playback
            try:
                sd.play(float_samples, samplerate=sample_rate)
                sd.wait()
            except Exception as play_err:
                print(f"[TTS] Playback error: {play_err}. Saving WAV for manual playback.")
                # On playback error, save a WAV to help the user manually play it
                try:
                    int16_samples = (np.clip(float_samples, -1.0, 1.0) * 32767).astype(np.int16)
                    if not wav_path:
                        fd, tmp_path = tempfile.mkstemp(prefix="golfcaddie_tts_", suffix=".wav")
                        os.close(fd)
                        wav_path = tmp_path
                    with wave.open(wav_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(sample_rate)
                        wf.writeframes(int16_samples.tobytes())
                    print(f"[TTS] Saved WAV: {wav_path}")
                except Exception as wav_err:
                    print(f"[TTS] Could not save WAV: {wav_err}")

            # Offer replay and optional delete
            if want_replay and wav_path:
                try:
                    if sys.stdin and sys.stdin.isatty():
                        while True:
                            ans = input("Replay audio? [y/N]: ").strip().lower()
                            if ans in ("y", "yes"):
                                try:
                                    sd.play(float_samples, samplerate=sample_rate)
                                    sd.wait()
                                except Exception as play_err2:
                                    print(f"[TTS] Replay error: {play_err2}")
                                    break
                            else:
                                break
                    else:
                        # Non-interactive: no replay possible
                        if os.getenv("GC_DEBUG"):
                            print("[TTS] Non-interactive session; skipping replay prompt.")
                except Exception as prompt_err:
                    print(f"[TTS] Prompt error: {prompt_err}")
                finally:
                    try:
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                            if os.getenv("GC_DEBUG"):
                                print("[TTS] Deleted WAV file.")
                    except Exception as del_err:
                        print(f"[TTS] Could not delete WAV: {del_err}")
            else:
                # Best-effort cleanup of legacy file path from older versions
                try:
                    legacy = os.path.abspath("tts_output.wav")
                    if os.path.exists(legacy) and not bool(os.getenv("GC_TTS_REPLAY")):
                        os.remove(legacy)
                        if os.getenv("GC_DEBUG"):
                            print(f"[TTS] Deleted legacy WAV file: {legacy}")
                except Exception:
                    pass
    except Exception as e:  # pragma: no cover
        print(f"Speechmatics TTS error: {type(e).__name__}: {e}; printing text:")
        print(text)


