import sys
import os
import json
import re
import requests
import yagmail
from ctransformers import AutoModelForCausalLM

# -------------------------
# CONSTANTS
# -------------------------

MODEL_PATH = "model/mistral-7b.gguf"
MAX_SAFE_USER_TOKENS = 350
MAX_CHUNK_TOKENS = 250

RESULT_API = os.environ.get("RESULT_API_URL")
SEND_FORM_API = os.environ.get("SEND_FORM_API_URL")
EMAIL_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")

# -------------------------
# MEMORY HANDLING
# -------------------------

memory = []

memory_file = sys.argv[6] if len(sys.argv) > 6 else None
if memory_file and os.path.exists(memory_file):
    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            memory = json.load(f)
            if not isinstance(memory, list):
                memory = []
    except Exception as e:
        print("⚠️ Invalid memory JSON, ignoring:", e)
        memory = []

def format_memory(messages, max_turns=5):
    formatted = []
    for msg in messages[-max_turns:]:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            formatted.append(f"<|user|>\n{content}")
        elif role == "assistant":
            formatted.append(f"<|assistant|>\n{content}")
    return "\n".join(formatted)

# -------------------------
# TOKEN ESTIMATION
# -------------------------

def estimate_tokens(text: str) -> int:
    return int(len(text.split()) / 0.75)

# -------------------------
# SPLITTING
# -------------------------

def rule_based_split(text: str):
    parts = re.split(r"\n?\s*\d+\.\s+", text)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]
    return [text.strip()]

SPLIT_SYSTEM_PROMPT = """
You analyze text and extract distinct questions.
Return ONLY a numbered list.
Do NOT answer anything.
"""

def ai_refine_split(model, chunks):
    refined = []
    for chunk in chunks:
        if estimate_tokens(chunk) > MAX_CHUNK_TOKENS:
            refined.append(chunk)
            continue

        prompt = f"""<|system|>
{SPLIT_SYSTEM_PROMPT}

<|user|>
{chunk}

<|assistant|>
"""
        output = model(prompt, max_new_tokens=200, temperature=0.2, top_p=0.9).strip()
        items = re.split(r"\n?\s*\d+\.\s+", output)
        items = [i.strip() for i in items if i.strip()]
        refined.extend(items if items else [chunk])
    return refined

def answer_chunks(model, base_prompt, questions):
    answers = []
    for i, q in enumerate(questions, 1):
        prompt = f"""{base_prompt}

<|user|>
Question {i}:
{q}

<|assistant|>
"""
        response = model(prompt, max_new_tokens=300, temperature=0.6, top_p=0.85).strip()
        answers.append(f"{i}. {response}")
    return "\n\n".join(answers)

# -------------------------
# SYSTEM PROMPTS
# -------------------------

PLATFORM_CONFIG = {
    "support": "You are a professional support AI. Append [SEND_FORM] if appropriate.",
    "student": "You are a student tutor. Explain clearly.",
    "portfolio": "You are a portfolio assistant. Append [SEND_FORM] when ready."
}

EMAIL_CONFIG = {
    "support": ("Support Update", "Support Bot"),
    "student": ("Learning Assistant", "Tutor Bot"),
    "portfolio": ("Project Discussion", "Portfolio Bot")
}

# -------------------------
# EMAIL
# -------------------------

def send_email(to_email, subject, body, sender_name):
    yag = yagmail.SMTP(
        user={"contactregteam@gmail.com": sender_name},
        password=EMAIL_PASSWORD,
    )
    yag.send(to=to_email, subject=subject, contents=body)

# -------------------------
# MAIN
# -------------------------

def main():
    if len(sys.argv) < 6:
        raise ValueError("Usage: tomer.py <question> <email> <platform> <incoming_id> <outgoing_id> [memory_file]")

    question, email, platform, incoming_id, outgoing_id = sys.argv[1:6]

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        model_type="mistral",
        context_length=2048,
        gpu_layers=0,
    )

    base_prompt = f"""<|system|>
{PLATFORM_CONFIG[platform]}

Conversation so far:
{format_memory(memory)}
"""

    if estimate_tokens(question) > MAX_SAFE_USER_TOKENS:
        chunks = ai_refine_split(model, rule_based_split(question))
        raw_answer = answer_chunks(model, base_prompt, chunks)
    else:
        prompt = f"""{base_prompt}

<|user|>
{question}

<|assistant|>
"""
        raw_answer = model(prompt, max_new_tokens=650, temperature=0.6, top_p=0.85).strip()

    send_form = "[SEND_FORM]" in raw_answer
    answer = raw_answer.replace("[SEND_FORM]", "").strip()

    requests.post(RESULT_API, json={
        "incoming_id": incoming_id,
        "outgoing_id": outgoing_id,
        "message": answer,
        "platform": platform,
        "email": email,
    }, timeout=10)

    subject, sender = EMAIL_CONFIG[platform]
    send_email(email, subject, answer, sender)

    if send_form:
        requests.post(SEND_FORM_API, json={
            "incoming_id": incoming_id,
            "outgoing_id": outgoing_id,
            "platform": platform,
        }, timeout=10)

    print("✅ Completed safely with chunked reasoning.")

if __name__ == "__main__":
    main()
