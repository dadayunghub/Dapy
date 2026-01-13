import os
import sys
import json
import math
import tempfile
import subprocess
from typing import List

import whisper
import yagmail
import nemo.collections.asr as nemo_asr
from omegaconf import OmegaConf
from nemo.collections.asr.models import ClusteringDiarizer

# =========================
# CONFIG
# =========================
MODEL_SIZE = "large"  # Whisper model
OUTPUT_DIR = "output"
DEVICE = "cpu"
FP16 = False

CHUNK_SECONDS = 30  # optional chunking for long audio
FORCED_LANGUAGE = "en"  # None for auto

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

def chunk_audio(path, chunk_seconds):
    """Optional: Split audio into chunks to avoid Whisper memory issues"""
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

def transcribe_chunks(model, chunks):
    """Transcribe each audio chunk with Whisper"""
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
# NE Mo SPEAKER DIARIZATION
# =========================
def diarize_segments_nemo(audio_path):
    """
    Perform real speaker diarization using cached NeMo VAD + ECAPA models.
    Returns a list of segments with start, end, speaker (text empty)
    """
    # Ensure cached models are loaded
    vad_model = nemo_asr.models.EncDecClassificationModel.from_pretrained(
        model_name="vad_telephony_marblenet"
    )
    spk_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained(
        model_name="ecapa_tdnn"
    )

    # Create dummy manifest
    manifest_path = "dummy_manifest.json"
    with open(manifest_path, "w") as f:
        f.write(json.dumps({
            "audio_filepath": audio_path,
            "offset": 0,
            "duration": 0,
            "label": "infer",
            "text": "-"
        }) + "\n")

    cfg = OmegaConf.create({
        "diarizer": {
            "manifest_filepath": manifest_path,
            "out_dir": "nemo_out",
            "vad": {"model_path": "vad_telephony_marblenet"},
            "speaker_embeddings": {"model_path": "ecapa_tdnn"},
            "clustering": {"parameters": {"oracle_num_speakers": False}}
        }
    })

    diarizer = ClusteringDiarizer(cfg=cfg)
    diarization_result = diarizer.diarize(audio_file=audio_path)

    diarized = []
    for seg in diarization_result:
        diarized.append({
            "speaker": seg["speaker"],
            "start": seg["start"],
            "end": seg["end"],
            "text": ""
        })
    return diarized

def align_speakers(whisper_segments, diarized_segments):
    """Assign speaker labels from diarization to Whisper transcription segments"""
    aligned = []
    for w in whisper_segments:
        for d in diarized_segments:
            if d["start"] <= w["start"] < d["end"] or (w["start"] <= d["start"] < w["end"]):
                w["speaker"] = d["speaker"]
                break
        else:
            w["speaker"] = "UNKNOWN"
        aligned.append(w)
    return aligned

# =========================
# SRT / VTT WRITERS
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
# EMAIL DELIVERY
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

    if not os.path.exists(audio_path):
        raise FileNotFoundError("Audio file not found")

    print(f"[DEBUG] Audio path: {audio_path}")
    print(f"[DEBUG] Audio size: {os.path.getsize(audio_path)/(1024*1024):.2f} MB")

    ensure_dir(OUTPUT_DIR)

    # Load Whisper
    print("[INFO] Loading Whisper model...")
    model = whisper.load_model(MODEL_SIZE, device=DEVICE)

    # Optional chunking for very long audio
    print("[INFO] Chunking audio...")
    chunks = chunk_audio(audio_path, CHUNK_SECONDS)
    print(f"[INFO] Total chunks: {len(chunks)}")

    # Transcribe
    print("[INFO] Transcribing audio...")
    segments = transcribe_chunks(model, chunks)

    # Speaker diarization with NeMo
    print("[INFO] Diarizing speakers...")
    diarized_segments = diarize_segments_nemo(audio_path)

    # Align Whisper transcription with speakers
    print("[INFO] Aligning speakers...")
    diarized = align_speakers(segments, diarized_segments)

    # Write outputs
    base = "transcript"
    txt_path = f"{OUTPUT_DIR}/{base}.txt"
    srt_path = f"{OUTPUT_DIR}/{base}.srt"
    vtt_path = f"{OUTPUT_DIR}/{base}.vtt"

    with open(txt_path, "w", encoding="utf-8") as f:
        for d in diarized:
            f.write(f"[{d['speaker']}] {d['text']}\n")

    write_srt(diarized, srt_path)
    write_vtt(diarized, vtt_path)

    # Save JSON result
    with open("result.json", "w") as f:
        json.dump(diarized, f, indent=2)

    # Send email
    print("[INFO] Sending email...")
    send_email(emails, [txt_path, srt_path, vtt_path])

    print("✅ DONE")

if __name__ == "__main__":
    main()
