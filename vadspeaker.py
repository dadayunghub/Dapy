# vadspeaker.py
import sys
import json
from omegaconf import OmegaConf
from nemo.collections.asr.models import ClusteringDiarizer

audio_path = sys.argv[1]
output_json = "speakers.json"

# Create NeMo manifest
manifest = {
    "audio_filepath": audio_path,
    "offset": 0,
    "duration": None,
    "label": "infer",
    "text": "-"
}

with open("manifest.json", "w") as f:
    f.write(json.dumps(manifest) + "\n")

cfg = OmegaConf.create({
    "diarizer": {
        "manifest_filepath": "manifest.json",
        "out_dir": "nemo_diar",
        "oracle_vad": False,
        "vad": {
            "model_path": "vad_telephony_marblenet"
        },
        "speaker_embeddings": {
            "model_path": "ecapa_tdnn"
        },
        "clustering": {
            "parameters": {
                "oracle_num_speakers": False
            }
        }
    }
})

print("[INFO] Running NeMo diarization...")
diarizer = ClusteringDiarizer(cfg=cfg)
diarizer.diarize()

# Parse RTTM
rttm_path = "nemo_diar/pred_rttms/manifest.rttm"
segments = []

with open(rttm_path) as f:
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
