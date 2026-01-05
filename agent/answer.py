# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import requests
from sentence_transformers import SentenceTransformer, util

# ---------------- CONFIG ----------------

HF_MODEL = "HuggingFaceH4/zephyr-7b-beta"


HF_API_URL = f"https://router.huggingface.co/models/{HF_MODEL}"
HF_TOKEN = os.environ.get("HF_API_TOKEN")

DOCS_PATH = "docs/company_info.json"
OUTPUT_PATH = "answers/latest.json"

MAX_RETRIES = 3
RETRY_DELAY = 5

# ---------------- SAFETY CHECKS ----------------

if not HF_TOKEN:
    raise RuntimeError("HF_API_TOKEN is not set in GitHub secrets.")

if len(sys.argv) < 2:
    raise RuntimeError("No question provided.")

question = sys.argv[1]

# ---------------- LOAD DOCUMENTS ----------------

with open(DOCS_PATH, "r", encoding="utf-8") as f:
    docs = json.load(f)

doc_texts = [d["text"] for d in docs]

# ---------------- EMBEDDINGS ----------------

embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

doc_embeddings = embedder.encode(
    doc_texts,
    convert_to_tensor=True,
    normalize_embeddings=True
)

question_embedding = embedder.encode(
    question,
    convert_to_tensor=True,
    normalize_embeddings=True
)

hits = util.semantic_search(question_embedding, doc_embeddings, top_k=2)
context = "\n".join(doc_texts[h["corpus_id"]] for h in hits[0])

# ---------------- PROMPT ----------------

prompt = f"""
You are a professional company support agent.
Answer ONLY using the information in the context.
If the answer is not in the context, say "I don't have that information."

Context:
{context}

Question:
{question}

Answer:
"""

# ---------------- HF INFERENCE ----------------

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

payload = {
    "inputs": prompt,
    "parameters": {
        "max_new_tokens": 200,
        "temperature": 0.3,
        "return_full_text": False
    }
}

result = None

for attempt in range(MAX_RETRIES):
    response = requests.post(
        HF_API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    try:
        result = response.json()
    except Exception:
        result = {
            "error": f"Non-JSON response (status {response.status_code})"
        }

    # Model loading → retry
    if isinstance(result, dict) and "error" in result:
        if "loading" in result["error"].lower():
            time.sleep(RETRY_DELAY)
            continue
        break

    # Success
    if isinstance(result, list):
        break

# ---------------- PARSE RESPONSE ----------------

if isinstance(result, list) and result and "generated_text" in result[0]:
    answer_text = result[0]["generated_text"].strip()
elif isinstance(result, dict) and "error" in result:
    answer_text = f"Error from Hugging Face API: {result['error']}"
else:
    answer_text = f"Unexpected response: {json.dumps(result)}"

# ---------------- SAVE ANSWER ----------------

os.makedirs("answers", exist_ok=True)

output = {
    "question": question,
    "answer": answer_text,
    "model": HF_MODEL,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("Answer written to answers/latest.json")
print(answer_text)
