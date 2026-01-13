# vadspeaker.py
import sys
import json
from omegaconf import OmegaConf
from nemo.collections.asr.models import ClusteringDiarizer

audio_path = sys.argv[1]
output_json = "speakers.json"

# -------------------------
# Create manifest
# -------------------------
with open("manifest.json", "w") as f:
    f.write(json.dumps({
        "audio_filepath": audio_path,
        "offset": 0,
        "duration": None,
        "label": "infer",
        "text": "-"
    }) + "\n")

# -------------------------
# REQUIRED NeMo config
# -------------------------
cfg = OmegaConf.create({
    "diarizer": {
        "manifest_filepath": "manifest.json",
        "out_dir": "nemo_diar",

        # REQUIRED
        "oracle_vad": False,

        "vad": {
            "model_path": "vad_telephony_marblenet",

            # REQUIRED EVEN IF DEFAULT
            "parameters": {
                "window_length_in_sec": 0.15,
                "shift_length_in_sec": 0.01,
                "smoothing": "median",
                "overlap": 0.5,
                "onset": 0.8,
                "offset": 0.6,
                "min_duration_on": 0.1,
                "min_duration_off": 0.1
            }
        },

        "speaker_embeddings": {
            "model_path": "ecapa_tdnn"
        },

        "clustering": {
            "parameters": {
                "oracle_num_speakers": False,
                "max_num_speakers": 8
            }
        }
    }
})

print("[INFO] Running NeMo diarization...")
diarizer = ClusteringDiarizer(cfg=cfg)
diarizer.diarize()

# -------------------------
# Parse RTTM
# -------------------------
rttm = "nemo_diar/pred_rttms/manifest.rttm"
segments = []

with open(rttm) as f:
    for line in f:
        p = line.strip().split()
        segments.append({
            "speaker": p[7],
            "start": float(p[3]),
            "end": float(p[3]) + float(p[4])
        })

with open(output_json, "w") as f:
    json.dump(segments, f, indent=2)

print("✅ speakers.json created")
