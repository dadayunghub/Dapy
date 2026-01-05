import sys
import json
from ctransformers import AutoModelForCausalLM

MODEL_PATH = "model/mistral-7b.gguf"

SYSTEM_PROMPT = """
be polite and helpful

"""

def main():
    if len(sys.argv) < 2:
        raise ValueError("No question provided")

    question = sys.argv[1]

    print("Loading mistral-7b model...")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        model_type="mistral",
        gpu_layers=0  # CPU only (GitHub Actions safe)
    )

    print("Generating answer...")

    prompt = f"""<|system|>
{SYSTEM_PROMPT.strip()}
<|user|>
{question}
<|assistant|>
"""

    answer = model(
        prompt,
        max_new_tokens=200,
        temperature=0.7,
        top_p=0.9,
    )

    with open("result.json", "w") as f:
        json.dump(
            {
                "question": question,
                "answer": answer.strip()
            },
            f,
            indent=2
        )

    print("DONE")

if __name__ == "__main__":
    main()
