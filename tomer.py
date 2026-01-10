import sys
import os
import json
import requests
import yagmail
from ctransformers import AutoModelForCausalLM

# -------------------------
# CONSTANTS
# -------------------------

MODEL_PATH = "model/mistral-7b.gguf"

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
    except Exception:
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
# SYSTEM PROMPTS
# -------------------------

SUPPORT_SYSTEM_PROMPT = """
You are a professional customer support AI assistant for Dave Company.

You must:
- Ask clarifying questions if information is missing
- Be professional, calm, and empathetic
- ONLY answer questions related to Dave Company

When you have fully understood the user's issue and collected all required details,
append this token on a new line:

[SEND_FORM]
"""

STUDENT_SYSTEM_PROMPT = """
You are a student-focused AI assistant.

Explain concepts step-by-step and clearly.
Ask follow-up questions when needed.
Do NOT send forms.
"""

PORTFOLIO_SYSTEM_PROMPT = """
You are a sales and portfolio assistant.

Your goal is to understand the customer's needs and project requirements.
Ask questions until all details are collected.

When all details are gathered, append this token on a new line:

[SEND_FORM]
"""

# -------------------------
# PLATFORM CONFIG
# -------------------------

PLATFORM_CONFIG = {
    "support": {
        "prompt": SUPPORT_SYSTEM_PROMPT,
        "rag": "dave_company.txt",
    },
    "student": {
        "prompt": STUDENT_SYSTEM_PROMPT,
        "rag": None,
    },
    "mediamarket": {
        "prompt": STUDENT_SYSTEM_PROMPT,
        "rag": None,
    },
    "portfolio": {
        "prompt": PORTFOLIO_SYSTEM_PROMPT,
        "rag": "portfolio.txt",
    },
}

EMAIL_CONFIG = {
    "support": {
        "subject": "Dave Company Support Update",
        "sender": "Dave Company Support",
    },
    "student": {
        "subject": "Your Learning Assistant Reply",
        "sender": "David AI Tutor",
    },
    "portfolio": {
        "subject": "Project Discussion Update",
        "sender": "David Portfolio Assistant",
    },
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
        raise ValueError(
            "Usage: python portfolio.py <question> <email> <platform> <incoming_id> <outgoing_id> [memory_json]"
        )

    question = sys.argv[1]
    email = sys.argv[2]
    platform = sys.argv[3]
    incoming_id = sys.argv[4]
    outgoing_id = sys.argv[5]

    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unsupported platform: {platform}")

    # -------------------------
    # Load platform config
    # -------------------------
    system_prompt = PLATFORM_CONFIG[platform]["prompt"]
    rag_path = PLATFORM_CONFIG[platform]["rag"]
    email_cfg = EMAIL_CONFIG[platform]

    # -------------------------
    # Load RAG
    # -------------------------
    rag_context = ""
    if rag_path and os.path.exists(rag_path):
        with open(rag_path, "r", encoding="utf-8") as f:
            rag_context = f.read()

    # -------------------------
    # Load model
    # -------------------------
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        model_type="mistral",
        gpu_layers=0,
    )

    # -------------------------
    # Build prompt
    # -------------------------
    memory_block = format_memory(memory)

    prompt = f"""<|system|>
{system_prompt.strip()}

Context:
{rag_context}

Conversation so far:
{memory_block}

<|user|>
{question}

<|assistant|>
"""

    # -------------------------
    # Generate answer
    # -------------------------
    raw_answer = model(
        prompt,
        max_new_tokens=450,
        temperature=0.6,
        top_p=0.85,
    ).strip()

    # -------------------------
    # Tool detection
    # -------------------------
    send_form = "[SEND_FORM]" in raw_answer
    answer = raw_answer.replace("[SEND_FORM]", "").strip()

    # -------------------------
    # Send message to DB API
    # -------------------------
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

    # -------------------------
    # Email fallback
    # -------------------------
    send_email(
        to_email=email,
        subject=email_cfg["subject"],
        body=answer,
        sender_name=email_cfg["sender"],
    )

    # -------------------------
    # Trigger SEND_FORM tool
    # -------------------------
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

    print("✅ Agent finished successfully.")

if __name__ == "__main__":
    main()
