"""
chatbot.py
Core logic for the AI Healthcare Chatbot: talks to OpenRouter's chat
completions API, holds the system prompt, and screens messages for
emergency/crisis language before they ever reach the model.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

_DISEASE_DATA_PATH = os.path.join(os.path.dirname(__file__), "disease_data.json")


def load_disease_data() -> dict:
    """Load the local disease reference dataset (symptoms/prevention/treatment/vaccination)."""
    try:
        with open(_DISEASE_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


DISEASE_DATA = load_disease_data()


def find_relevant_diseases(text: str) -> list:
    """Return names of diseases from disease_data.json mentioned in the given text."""
    lowered = text.lower()
    return [name for name in DISEASE_DATA if name.lower() in lowered]


def build_disease_context(disease_names: list) -> str:
    """Format reference data for the given diseases into a compact context block
    that can be injected into the conversation so the model grounds its answer
    in this vetted data rather than relying purely on its own knowledge."""
    if not disease_names:
        return ""

    lines = ["Reference data (use this as your primary source for these conditions):"]
    for name in disease_names:
        info = DISEASE_DATA.get(name)
        if not info:
            continue
        lines.append(f"\n{name}:")
        lines.append(f"- Symptoms: {', '.join(info.get('symptoms', []))}")
        lines.append(f"- Prevention: {', '.join(info.get('prevention', []))}")
        lines.append(f"- Treatment: {info.get('treatment', 'N/A')}")
        lines.append(f"- Vaccination: {info.get('vaccination', 'N/A')}")
    return "\n".join(lines)

# Sensible free/low-cost default; can be overridden via .env or the UI.
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

SYSTEM_PROMPT = """You are HealthGuide AI, a friendly and knowledgeable general health
information assistant.

Your role:
- Answer general health, wellness, nutrition, fitness, and medical-topic questions in
  clear, plain language.
- Explain symptoms, conditions, treatments, and medications at a general educational level.
- Encourage healthy habits and evidence-based information.
- Always be calm, empathetic, and non-alarmist.

Strict boundaries:
- You do NOT diagnose. Never say "you have X"; instead say things like "these symptoms
  can sometimes be associated with X, Y, or Z, but only a healthcare provider can diagnose you."
- You do NOT prescribe medications or exact dosages. You can explain what a class of
  medication is generally used for.
- For anything urgent, severe, or ambiguous, recommend the person see a licensed
  clinician or seek in-person/emergency care.
- You are not a substitute for professional medical advice, diagnosis, or treatment.
- If asked about topics unrelated to health, gently redirect back to health topics.

Tone: warm, clear, concise. Use short paragraphs or bullet points for readability.
Always end responses that involve symptoms or conditions with a brief reminder to consult
a healthcare professional for personal medical advice.
"""

# Keywords/phrases that should trigger an immediate emergency banner rather than
# (or in addition to) a normal conversational answer. Kept intentionally broad;
# false positives are far cheaper than false negatives here.
EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "severe bleeding", "heavy bleeding", "unconscious", "not breathing",
    "stroke", "face drooping", "slurred speech", "overdose", "poisoning",
    "suicide", "suicidal", "kill myself", "end my life", "want to die",
    "self harm", "self-harm", "hurting myself", "severe allergic reaction",
    "anaphylaxis", "can't feel my", "seizure", "heart attack",
]

EMERGENCY_MESSAGE = """🚨 **This may be a medical emergency.**

If you or someone else is in immediate danger, please:
- **Call your local emergency number right now** (e.g. 911 in the US, 112 in the EU, 999 in the UK).
- Go to the nearest emergency room, or
- If this involves thoughts of suicide or self-harm, you can also reach the **988 Suicide & Crisis Lifeline** (call or text 988 in the US), or a local equivalent.

I'm an AI assistant and can't provide emergency care. Please reach out to a real person or emergency service right away — you don't have to handle this alone.
"""


def contains_emergency_language(text: str) -> bool:
    """Return True if the user's message contains language suggesting a
    possible emergency or crisis situation."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in EMERGENCY_KEYWORDS)


def get_response(messages, model: str = DEFAULT_MODEL, temperature: float = 0.5) -> str:
    """
    Send the conversation to OpenRouter and return the assistant's reply text.

    messages: list of {"role": "user"|"assistant", "content": str} (no system message —
              it's injected here automatically). If the most recent user message mentions
              a disease covered in disease_data.json, its reference data is injected as
              an extra system message so the answer is grounded in that vetted data.
    """
    if not OPENROUTER_API_KEY:
        return (
            "⚠️ No OpenRouter API key found. Please set `OPENROUTER_API_KEY` in your "
            "`.env` file to enable responses."
        )

    system_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if messages:
        last_user_text = messages[-1].get("content", "")
        relevant = find_relevant_diseases(last_user_text)
        context = build_disease_context(relevant)
        if context:
            system_messages.append({"role": "system", "content": context})

    payload_messages = system_messages + messages

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost:8501",
        "X-Title": "AI Healthcare Chatbot",
    }

    payload = {
        "model": model,
        "messages": payload_messages,
        "temperature": temperature,
        "max_tokens": 800,
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        return "⚠️ The request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        return f"⚠️ API error ({response.status_code}): {e}"
    except (KeyError, IndexError, ValueError):
        return "⚠️ Received an unexpected response from the model. Please try again."
    except requests.exceptions.RequestException as e:
        return f"⚠️ Network error: {e}"