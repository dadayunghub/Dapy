import os
import sys
import json
import math
import tempfile
import whisper
import yagmail
import subprocess
from typing import List

# =========================
# CONFIG
# =========================
MODEL_SIZE = "large"
OUTPUT_DIR = "output"
DEVICE = "cpu"
FP16 = False

# Chunking
CHUNK_SECONDS = 30

# Language forcing (None = auto)
FORCED_LANGUAGE = "en"

# =========================
# UTILS
# =========================
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def run(cmd):
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()

def get_audio_duration(path):
    return float(run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]).strip())

# =========================
# AGENT 1: AUDIO CHUNKER
# =========================
def chunk_audio(path, chunk_seconds):
    duration = get_audio_duration(path)
    print(f"[DEBUG] Audio duration: {duration:.2f}s")

    chunks = []
    total = math.ceil(duration / chunk_seconds)

    for i in range(total):
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

        if not os.path.exists(out) or os.path.getsize(out) < 10_000:
            raise RuntimeError(f"Chunk {i} failed to generate")

        print(f"[DEBUG] Chunk {i+1}/{total} created ({os.path.getsize(out)/1024:.1f} KB)")
        chunks.append((out, start))

    return chunks

# =========================
# AGENT 2: TRANSCRIPTION
# =========================
def transcribe_chunks(model, chunks):
    segments = []

    for i, (chunk_path, offset) in enumerate(chunks, 1):
        print(f"[INFO] Transcribing chunk {i}/{len(chunks)}")

        result = model.transcribe(
            chunk_path,
            fp16=FP16,
            language=FORCED_LANGUAGE,
            verbose=False
        )

        for seg in result["segments"]:
            seg["start"] += offset
            seg["end"] += offset
            segments.append(seg)

        os.remove(chunk_path)

    return segments

# =========================
# AGENT 3: DIARIZATION (simple, CPU-safe)
# =========================
def load_speakers(path="speakers.json"):
    with open(path) as f:
        return json.load(f)

def find_speaker(start, end, speakers):
    for s in speakers:
        if start >= s["start"] and end <= s["end"]:
            return s["speaker"]
    return "UNKNOWN"


# =========================
# AGENT 4: SUBTITLES
# =========================
def write_srt(segments, path):
    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{ts(s['start'])} --> {ts(s['end'])}\n")
            f.write(f"[{s['speaker']}] {s['text']}\n\n")

def write_vtt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for s in segments:
            f.write(f"{s['start']:.3f} --> {s['end']:.3f}\n")
            f.write(f"[{s['speaker']}] {s['text']}\n\n")

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
        subject="Whisper Transcription",
        contents="Attached are your transcription files.",
        attachments=attachments
    )

# =========================
# MAIN
# =========================
def main():
    audio_path = sys.argv[1]
    emails = sys.argv[2]

    print(f"[DEBUG] Audio path: {audio_path}")

    if not os.path.exists(audio_path):
        raise FileNotFoundError("Audio file not found")

    print(f"[DEBUG] Audio size: {os.path.getsize(audio_path)/(1024*1024):.2f} MB")

    ensure_dir(OUTPUT_DIR)

    print("[INFO] Loading Whisper model...")
    model = whisper.load_model(MODEL_SIZE, device=DEVICE)

    print("[INFO] Chunking audio...")
    chunks = chunk_audio(audio_path, CHUNK_SECONDS)

    print("[INFO] Transcribing...")
    segments = transcribe_chunks(model, chunks)

    print("[INFO] Loading speaker segments...")
    speakers = load_speakers()

    diarized = []
    for seg in segments:
        diarized.append({
            "speaker": find_speaker(seg["start"], seg["end"], speakers),
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        })


    base = "transcript"
    txt = f"{OUTPUT_DIR}/{base}.txt"
    srt = f"{OUTPUT_DIR}/{base}.srt"
    vtt = f"{OUTPUT_DIR}/{base}.vtt"

    with open(txt, "w", encoding="utf-8") as f:
        for d in diarized:
            f.write(f"[{d['speaker']}] {d['text']}\n")

    write_srt(diarized, srt)
    write_vtt(diarized, vtt)

    with open("result.json", "w") as f:
        json.dump(diarized, f, indent=2)

    send_email(emails, [txt, srt, vtt])

    print("✅ DONE")

if __name__ == "__main__":
    main()
