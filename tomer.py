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
MAX_SAFE_USER_TOKENS = 350   # user message only
MAX_CHUNK_TOKENS = 250

RESULT_API = os.environ.get("RESULT_API_URL")
SEND_FORM_API = os.environ.get("SEND_FORM_API_URL")
EMAIL_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")

# -------------------------
# MEMORY HANDLING
# -------------------------

memory = []

if len(sys.argv) >= 7 and sys.argv[6]:
    try:
        memory = json.loads(sys.argv[6])
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
    # Approximation safe for Mistral
    return int(len(text.split()) / 0.75)

# -------------------------
# RULE-BASED SPLITTER (SAFE)
# -------------------------

def rule_based_split(text: str):
    text = text.strip()

    # Split numbered lists
    parts = re.split(r"\n?\s*\d+\.\s+", text)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    # Split by question-like keywords
    keywords = [
        "how", "what", "why", "when", "where",
        "can you", "should i", "is it", "do i"
    ]

    lines = re.split(r"\n+", text)
    chunks = []

    buffer = ""
    for line in lines:
        if any(line.lower().startswith(k) for k in keywords):
            if buffer:
                chunks.append(buffer.strip())
            buffer = line
        else:
            buffer += " " + line

    if buffer.strip():
        chunks.append(buffer.strip())

    return chunks if chunks else [text]

# -------------------------
# AI REFINEMENT SPLITTER (OPTIONAL)
# -------------------------

SPLIT_SYSTEM_PROMPT = """
You are a text analysis assistant.

Task:
- Analyze the provided text
- Identify distinct questions or requests
- Rewrite each as a short, clear standalone question
- Return them as a numbered list
- Do NOT answer the questions
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

        # Parse numbered list
        items = re.split(r"\n?\s*\d+\.\s+", output)
        items = [i.strip() for i in items if i.strip()]

        refined.extend(items if items else [chunk])

    return refined

# -------------------------
# CHUNK ANSWERING
# -------------------------

def answer_chunks(model, base_prompt, questions):
    answers = []

    for i, q in enumerate(questions, 1):
        prompt = f"""
{base_prompt}

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

SUPPORT_SYSTEM_PROMPT = """
You are a professional customer support AI assistant for Dave Company.

ONLY answer questions related to Dave Company.
Ask clarifying questions if needed.

When complete, append:
[SEND_FORM]
"""

STUDENT_SYSTEM_PROMPT = """
You are a student-focused AI assistant.

Explain clearly and step-by-step.
"""

PORTFOLIO_SYSTEM_PROMPT = """
You are a sales and portfolio assistant.

Ask questions until requirements are complete.

When ready, append:
[SEND_FORM]
"""

PLATFORM_CONFIG = {
    "support": SUPPORT_SYSTEM_PROMPT,
    "student": STUDENT_SYSTEM_PROMPT,
    "portfolio": PORTFOLIO_SYSTEM_PROMPT,
}

EMAIL_CONFIG = {
    "support": ("Dave Company Support Update", "Dave Company Support"),
    "student": ("Your Learning Assistant Reply", "David AI Tutor"),
    "portfolio": ("Project Discussion Update", "David Portfolio Assistant"),
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
        raise ValueError("Usage: tomer.py <question> <email> <platform> <incoming_id> <outgoing_id> [memory_json]")

    question, email, platform, incoming_id, outgoing_id = sys.argv[1:6]

    system_prompt = PLATFORM_CONFIG[platform]
    subject, sender = EMAIL_CONFIG[platform]

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        model_type="mistral",
        context_length=2048,
        gpu_layers=0,
    )

    memory_block = format_memory(memory)

    base_prompt = f"""<|system|>
{system_prompt}

Conversation so far:
{memory_block}
"""

    if estimate_tokens(question) > MAX_SAFE_USER_TOKENS:
        chunks = rule_based_split(question)
        chunks = ai_refine_split(model, chunks)
        raw_answer = answer_chunks(model, base_prompt, chunks)
    else:
        prompt = f"""
{base_prompt}

<|user|>
{question}

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

    print("✅ Completed safely with chunked reasoning.")

if __name__ == "__main__":
    main()
