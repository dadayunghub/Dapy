import os
import sys
import json
import math
import tempfile
import requests
import whisper
import yagmail
import subprocess
from urllib.parse import urlparse
from typing import List

# =========================
# CONFIG
# =========================
MODEL_SIZE = "large"
MODEL_DIR = "model"
OUTPUT_DIR = "output"
DEVICE = "cpu"
FP16 = False

# Chunking
CHUNK_SECONDS = 30  # >= 30 sec as requested

# Language forcing (set to None for auto-detect)
FORCED_LANGUAGE = "en"   # e.g. "en", "fr", "es", or None

# Silence threshold for diarization
SILENCE_DB = -35

# =========================
# UTILS
# =========================
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def is_url(path):
    return urlparse(path).scheme in ("http", "https")

def download_audio(url):
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    suffix = os.path.splitext(urlparse(url).path)[1] or ".audio"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return path

def get_audio_duration(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    return float(subprocess.check_output(cmd).decode().strip())

# =========================
# AGENT 1: AUDIO CHUNKER
# =========================
def chunk_audio(path, chunk_seconds):
    duration = get_audio_duration(path)
    chunks = []

    for i in range(0, math.ceil(duration / chunk_seconds)):
        start = i * chunk_seconds
        out = tempfile.mktemp(suffix=".wav")

        cmd = [
            "ffmpeg", "-y",
            "-i", path,
            "-ss", str(start),
            "-t", str(chunk_seconds),
            "-ac", "1",
            "-ar", "16000",
            out
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        chunks.append((out, start))

    return chunks

# =========================
# AGENT 2: TRANSCRIPTION
# =========================
def transcribe_chunks(model, chunks):
    all_segments = []

    for chunk_path, offset in chunks:
        result = model.transcribe(
            chunk_path,
            fp16=FP16,
            language=FORCED_LANGUAGE,
            verbose=False
        )

        for seg in result["segments"]:
            seg["start"] += offset
            seg["end"] += offset
            all_segments.append(seg)

        os.remove(chunk_path)

    return all_segments

# =========================
# AGENT 3: DIARIZATION (CPU SAFE)
# =========================
def diarize_segments(segments):
    speaker = 1
    last_end = 0
    diarized = []

    for seg in segments:
        gap = seg["start"] - last_end
        if gap > 1.2:
            speaker += 1

        diarized.append({
            "speaker": f"SPEAKER {speaker}",
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        })
        last_end = seg["end"]

    return diarized

# =========================
# AGENT 4: SUBTITLE WRITER
# =========================
def write_srt(segments, path):
    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{ts(seg['start'])} --> {ts(seg['end'])}\n")
            f.write(f"[{seg['speaker']}] {seg['text']}\n\n")

def write_vtt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            f.write(f"{seg['start']:.3f} --> {seg['end']:.3f}\n")
            f.write(f"[{seg['speaker']}] {seg['text']}\n\n")

# =========================
# AGENT 5: DELIVERY
# =========================
def send_email(to, attachments):
    yag = yagmail.SMTP(
        os.environ["EMAIL_USER"],
        os.environ["EMAIL_PASS"]
    )
    yag.send(
        to=to.split(","),
        subject="Whisper Transcription (Chunked + Diarized)",
        contents="Attached are the transcription results.",
        attachments=attachments
    )

# =========================
# MAIN PIPELINE
# =========================
def main():
    audio_input = sys.argv[1]
    emails = sys.argv[2]

    ensure_dir(OUTPUT_DIR)

    if is_url(audio_input):
        audio_path = download_audio(audio_input)
        cleanup = True
    else:
        audio_path = audio_input
        cleanup = False

    print("[INFO] Loading Whisper model...")
    model = whisper.load_model(MODEL_SIZE, device=DEVICE, download_root=MODEL_DIR)

    print("[INFO] Chunking audio...")
    chunks = chunk_audio(audio_path, CHUNK_SECONDS)

    print("[INFO] Transcribing chunks...")
    segments = transcribe_chunks(model, chunks)

    print("[INFO] Diarizing speakers...")
    diarized = diarize_segments(segments)

    base = "transcript"
    txt = f"{OUTPUT_DIR}/{base}.txt"
    srt = f"{OUTPUT_DIR}/{base}.srt"
    vtt = f"{OUTPUT_DIR}/{base}.vtt"

    with open(txt, "w", encoding="utf-8") as f:
        for d in diarized:
            f.write(f"[{d['speaker']}] {d['text']}\n")

    write_srt(diarized, srt)
    write_vtt(diarized, vtt)

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(diarized, f, indent=2)

    send_email(emails, [txt, srt, vtt])

    if cleanup:
        os.remove(audio_path)

    print("✅ DONE")

if __name__ == "__main__":
    main()
