import sys
import os
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
# TOKEN ESTIMATION
# -------------------------

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return int(len(text.split()) / 0.75)

# -------------------------
# SPLITTING LOGIC
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

        output = model(
            prompt,
            max_new_tokens=200,
            temperature=0.2,
            top_p=0.9,
        ).strip()

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
        response = model(
            prompt,
            max_new_tokens=300,
            temperature=0.6,
            top_p=0.85,
        ).strip()

        answers.append(f"{i}. {response}")

    return "\n\n".join(answers)

# -------------------------
# SYSTEM PROMPTS
# -------------------------

PLATFORM_CONFIG = {
    "support": "You are a professional support AI. Append [SEND_FORM] if appropriate.",
    "student": "You are a student tutor. Explain clearly.",
    "portfolio": "You are a portfolio assistant. Append [SEND_FORM] when ready.",
}

EMAIL_CONFIG = {
    "support": ("Support Update", "Support Bot"),
    "student": ("Learning Assistant", "Tutor Bot"),
    "portfolio": ("Project Discussion", "Portfolio Bot"),
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
# QUESTION FILE PARSING
# -------------------------

def parse_question_file(path: str):
    """
    question.txt contains conversation so far.
    Last non-empty line is the current user message.
    Everything before it is conversation context.
    """
    if not os.path.exists(path):
        return "", ""

    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    if not lines:
        return "", ""

    if len(lines) == 1:
        return "", lines[0]

    return "\n".join(lines[:-1]), lines[-1]

# -------------------------
# MAIN
# -------------------------

def main():
    if len(sys.argv) < 6:
        raise ValueError(
            "Usage: tomer.py <question.txt> <email> <platform> <incoming_id> <outgoing_id>"
        )

    question_file, email, platform, incoming_id, outgoing_id = sys.argv[1:6]

    conversation_so_far, current_question = parse_question_file(question_file)

    # New conversation safety
    if not current_question:
        current_question = "Hello."

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        model_type="mistral",
        context_length=2048,
        gpu_layers=0,
    )

    base_prompt = f"""<|system|>
{PLATFORM_CONFIG[platform]}

Conversation so far:
{conversation_so_far}
"""

    # ---------- ANSWERING ----------
    if estimate_tokens(current_question) > MAX_SAFE_USER_TOKENS:
        chunks = ai_refine_split(model, rule_based_split(current_question))
        raw_answer = answer_chunks(model, base_prompt, chunks)
    else:
        prompt = f"""{base_prompt}

<|user|>
{current_question}

<|assistant|>
"""
        raw_answer = model(
            prompt,
            max_new_tokens=650,
            temperature=0.6,
            top_p=0.85,
        ).strip()

    send_form = "[SEND_FORM]" in raw_answer
    answer = raw_answer.replace("[SEND_FORM]", "").strip()

    # ---------- SEND RESULT ----------
    requests.post(
        RESULT_API,
        json={
            "incoming_id": incoming_id,
            "outgoing_id": outgoing_id,
            "message": answer,
            "platform": platform,
            "email": email,
        },
        timeout=10,
    )

    subject, sender = EMAIL_CONFIG[platform]
    send_email(email, subject, answer, sender)

    if send_form:
        requests.post(
            SEND_FORM_API,
            json={
                "incoming_id": incoming_id,
                "outgoing_id": outgoing_id,
                "platform": platform,
            },
            timeout=10,
        )

    print("✅ Completed safely (stateless, no memory).")

if __name__ == "__main__":
    main()
