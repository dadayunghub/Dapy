import sys
import os
import re
import requests
import smtplib
from email.message import EmailMessage
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
        <tr>
  <td align='center' style='padding-top:20px;'>
    <a href='{reply_link}'
       style='
         display:inline-block;
         padding:12px 20px;
         background-color:#2563eb;
         color:#ffffff;
         text-decoration:none;
         font-weight:600;
         border-radius:4px;
         font-family:Arial, sans-serif;
       '>
       ✉️ 
    </a>
  </td>
</tr>

        """

    return f"""
<html>
  <body style='margin:0;padding:0;background-color:#f4f4f5;'>
  <table width='100%' cellpadding='0' cellspacing='0'>
    <tr>
      <td align='center' style='padding:20px;'>
        <table width='100%' max-width='600' cellpadding='0' cellspacing='0'
               style='background:#ffffff;border-radius:6px;padding:20px;'>

          <tr>
            <td style='
              font-family:Arial, sans-serif;
              font-size:15px;
              line-height:1.6;
              color:#111827;
            '>
              {message}
            </td>
          </tr>

          {button_html}

          <tr>
            <td style='
              padding-top:30px;
              font-size:12px;
              color:#6b7280;
              font-family:Arial, sans-serif;
              text-align:center;
            '>
              Mediamarket @ 2026.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>

</html>
"""


# -------------------------
# TOKEN ESTIMATION
# -------------------------


FORBIDDEN_WORDS = [
    
    "json",
    "schema",
]

SAFE_FALLBACK_MESSAGE = (
    "What!!. "
    " OK."
)

def parse_model_output(raw: str):
    try:
        parsed = json.loads(raw)

        message = parsed.get("message", "").strip()
        actions = parsed.get("actions", {})
        send_form = bool(actions.get("send_form", False))

        if not message:
            raise ValueError("Empty message")

        # 🚨 POLICY ENFORCEMENT
        lowered = message.lower()
        if any(word in lowered for word in FORBIDDEN_WORDS):
            print("⚠️ Policy violation detected. Message sanitized.")
            message = SAFE_FALLBACK_MESSAGE

        return message, send_form

    except Exception as e:
        print("⚠️ JSON parse failed:", e)
        print("⚠️ Raw model output:", raw)

        # Never leak raw output
        return SAFE_FALLBACK_MESSAGE, False


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
You are Mediamarket Customer Support and Mediamarket is a platform where users buy Goods and services

ROLE:
You ONLY have Conversations with users to know their issues and acknowledge them by telling the user that they need to verify their account to proceed and assure them their issues will be rectified immediately

LANGUAGE RULE (VERY IMPORTANT):
- Detect the language used by the user
- Give your reply in the SAME language as the user's message


ABSOLUTE RULES (MUST FOLLOW):
- Respond ONLY with valid JSON



MESSAGE RULES:
- The message must be a short, polite acknowledgement
- Never give instructions , steps or contacts suggestions

FORM TRIGGER LOGIC:
- Set "send_form" to true ONLY if the user has clearly explained their problem and you have acknowledged the users problem
- Otherwise set it to false

JSON SCHEMA (EXACT):
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

def send_email_html(to_email, subject, html_body, sender_name):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <contactregteam@gmail.com>"
    msg["To"] = to_email

    # Plain-text fallback (important)
    msg.set_content("Please view this message in an HTML-compatible email client.")

    # HTML version
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login("contactregteam@gmail.com", EMAIL_PASSWORD)
        server.send_message(msg)
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
    send_email_html(email, subject, body, sender)

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
