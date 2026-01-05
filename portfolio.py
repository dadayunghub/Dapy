import sys
import json
import os
from ctransformers import AutoModelForCausalLM
import yagmail

MODEL_PATH = "model/mistral-7b.gguf"
RAG_PATH = "dave_company.txt"

# ---------- SYSTEM PROMPTS ----------
SUPPORT_SYSTEM_PROMPT = """
You are a professional customer support AI assistant for Dave Company.

You ONLY answer questions or complaints related to Dave Company.
If the input is unrelated, respond politely that the request is not applicable
to Dave Company support.

Be clear, professional, and empathetic.
"""

STUDENT_SYSTEM_PROMPT = """
You are a student-focused AI assistant.

Explain concepts step-by-step, clearly, and in detail.
Assume the student wants learning-oriented answers, not short replies.
"""

# ---------- EMAIL ----------
def send_emails(subject, body, emails, sender):
    """
    Batch email sender using yagmail
    """
    yag = yagmail.SMTP(
        user={'contactregteam@gmail.com': sender},
        password="cfov ytcx gnpq drbx"
    )

    yag.send(
        to=emails,
        subject=subject,
        contents=body
    )


# ---------- MAIN ----------
def main():
    if len(sys.argv) < 4:
        raise ValueError("Usage: python agent.py <question> <emails_json> <action>")

    question = sys.argv[1]
    emails = json.loads(sys.argv[2])  # ["a@x.com", "b@y.com"]
    action = sys.argv[3]              # single | multiple

    # Choose system prompt
    if action == "single":
        SYSTEM_PROMPT = SUPPORT_SYSTEM_PROMPT
    elif action == "multiple":
        SYSTEM_PROMPT = STUDENT_SYSTEM_PROMPT
    else:
        raise ValueError("Invalid action")

    # Load RAG context (only for support agent)
    rag_context = ""
    if action == "single" and os.path.exists(RAG_PATH):
        with open(RAG_PATH, "r") as f:
            rag_context = f.read()

    print("Loading Mistral model...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        model_type="mistral",
        gpu_layers=0
    )

    # Build prompt
    prompt = f"""<|system|>
{SYSTEM_PROMPT.strip()}

Context:
{rag_context}

<|user|>
{question}

<|assistant|>
"""

    print("Generating answer...")
    answer = model(
        prompt,
        max_new_tokens=400,
        temperature=0.6,
        top_p=0.85
    ).strip()

    # Save result
    with open("result.json", "w") as f:
        json.dump(
            {
                "action": action,
                "question": question,
                "emails": emails,
                "answer": answer
            },
            f,
            indent=2
        )

    # Email behavior
    if action == "single":
        send_emails(
            subject="Dave Support Response",
            body=answer,
            emails=[emails[0]], sender="David portfolio Dave Company Support"
        )
    else:
        send_emails(
            subject="Student AI Answer",
            body=answer,
            emails=emails, sender="David Portfolio AI Student Assistant"

        )

    print("DONE")


if __name__ == "__main__":
    main()
