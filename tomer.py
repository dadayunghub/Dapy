import sys
import os
import re
import requests
import yagmail
import html
import json
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


def build_email_html(message: str, reply_link: str | None = None) -> str:
    """
    Builds a clean HTML email with optional reply button.
    Inline CSS only (email-safe).
    """

    button_html = ""
    if reply_link:
        button_html = f"""
        
  
    <a href=\'{reply_link}\'
       style=\'
         display:inline-block;
         padding:12px 20px;
         background-color:#2563eb;
         color:#ffffff;
         text-decoration:none;
         font-weight:600;
         border-radius:4px;
         font-family:Arial, sans-serif;
       \'>
       reply
    </a>
 

        """

    return f"""
<html>
  <body style='margin:0;padding:0;background-color:#f4f4f5;'>
  <h3>
              {message}
            </h3>
          

          {button_html}

          <p>
              This message was sent automatically. Please do not reply directly.
            </p>
          
</body>

</html>
"""


# -------------------------
# TOKEN ESTIMATION
# -------------------------


def parse_model_output(raw: str):
    """
    Strict JSON parser with safe fallback.
    """
    try:
        parsed = json.loads(raw)

        message = parsed.get("message", "").strip()
        actions = parsed.get("actions", {})

        send_form = bool(actions.get("send_form", False))

        if not message:
            raise ValueError("Empty message")

        return message, send_form

    except Exception as e:
        # HARD FAILSAFE — never block user
        print("⚠️ JSON parse failed:", e)
        print("⚠️ Raw model output:", raw)

        return raw.strip(), False


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
    "support": """
You are a professional Spanish-speaking support assistant.

IMPORTANT RULES:
- Respond ONLY with valid JSON
- Do NOT include markdown
- Do NOT include explanations
- Do NOT include extra keys

JSON SCHEMA:
{
  "message": string,
  "actions": {
    "send_form": boolean
  }
}

Set "send_form" to true ONLY if the user ask for the form.
""",

    "media": """
You are MDEA Customer Support, a professional customer service assistant for the MDEA platform.

MDEA is a global marketplace where users buy and sell goods and services across multiple countries.

Your goal is to:
- Understand the user’s problem clearly
- Acknowledge receipt of the complaint in a calm and reassuring tone
- Briefly confirm the type of issue based on the user’s description (login, transaction, delay, or other)
- Inform the user that the issue will be resolved after account verification

IMPORTANT BEHAVIOR RULES:
- Reply in the SAME language used by the user
- Be polite, professional, and supportive
- Do NOT ask for sensitive information directly
- Do NOT send the verification form until the user has clearly explained their issue

FORM TRIGGER RULE:
- Set "send_form" to true ONLY when the user has provided a clear and complete explanation of their problem
- If the problem is unclear or incomplete, ask the user for more details and keep "send_form" false

STRICT RESPONSE FORMAT RULES:
- Respond ONLY with valid JSON
- Do NOT include markdown
- Do NOT include explanations
- Do NOT include extra keys

JSON SCHEMA:
{
  "message": string,
  "actions": {
    "send_form": boolean
  }
}

""",

    "portfolio": """
You are a portfolio assistant.

IMPORTANT RULES:
- Respond ONLY with valid JSON

JSON SCHEMA:
{
  "message": string,
  "actions": {
    "send_form": boolean
  }
}

Set "send_form" to true if the user shows interest in collaboration or contact.
"""
}


EMAIL_CONFIG = {
    "support": ("Support Update", "Support Bot"),
    "media": ("Mediamarket", "MediaMkt"),
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
    yag.send(to=to_email, subject=subject, contents=body, headers={
            "Content-Type": "text/html; charset=UTF-8"
        })

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
    if len(sys.argv) < 7:
        raise ValueError(
            "Usage: tomer.py <question.txt> <email> <link> <platform> <incoming_id> <outgoing_id>"
        )

    question_file, email, link, platform, incoming_id, outgoing_id = sys.argv[1:7]

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

    answer, send_form = parse_model_output(raw_answer)


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
    safe_message = html.escape(answer).replace("\n", "<br>")

    body = build_email_html(
    message=safe_message,
    reply_link=link
    )
    send_email(email, subject, body, sender)

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
