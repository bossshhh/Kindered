import os
import re
from dotenv import load_dotenv

load_dotenv()

BANNED_META = re.compile(
    r"(?i)("
    r"\bas an ai\b|"
    r"\bi['’]?m (?:just )?(?:an )?ai\b|"
    r"\bartificial intelligence\b|"
    r"\bchatbot\b|"
    r"\blanguage model\b|"
    r"\bdigital twin\b|"
    r"\binformation i['’]?ve (?:received|been (?:given|provided))\b|"
    r"\bi don['’]?t have any (?:doctor )?notes?\b|"
    r"\bin (?:my|the) (?:context|database|system|training)\b|"
    r"\bi (?:wasn['’]?t|was not) (?:provided|given)\b|"
    r"\bbased on (?:the )?(?:information|data|context) (?:i|provided)\b|"
    r"\bi cannot access\b|"
    r"\bas a language model\b"
    r")"
)


def generate_response(
    system_prompt: str,
    message: str,
    history: list[dict],
    risk: str = "low",
    intent: str = "social",
    patient: dict | None = None,
    relative: dict | None = None,
):
    patient = patient or {}
    relative = relative or {}
    if risk == "critical":
        name = (relative.get("name") or "I").split()[0]
        if intent == "fall_safety" or "fell" in message.lower() or "slipped" in message.lower():
            return (
                f"Oh no — stay still if you can. Call out for someone nearby, or phone emergency help right now. "
                f"I’m {name}, and I need a real person there with you. Please get help now.",
                "safety_gate",
            )
        return (
            f"I’m so glad you told me. Please call emergency services or someone nearby right now, and stay on the line with them. "
            f"It’s {name} — I love you. Get a real person with you this second.",
            "safety_gate",
        )

    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if api_key in {"your_groq_api_key_here", "your-groq-api-key-here"}:
        api_key = ""
    if demo_mode or not api_key:
        return demo_response(message, risk, patient=patient, relative=relative, intent=intent), "demo"

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend({"role": h["role"], "content": h["content"]} for h in history[-8:] if h.get("role") in {"user", "assistant"})
        messages.append({"role": "user", "content": message})
        completion = client.chat.completions.create(
            messages=messages,
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0.4,
            max_tokens=220,
        )
        text = (completion.choices[0].message.content or "").strip()
        if text:
            cleaned = sanitize_response(text)
            if looks_like_meta(cleaned):
                return demo_response(message, risk, patient=patient, relative=relative, intent=intent), "persona_fallback"
            return cleaned, "groq"
    except Exception as e:
        print(f"GROQ_ERROR: {type(e).__name__}: {e}", flush=True)

    return demo_response(message, risk, patient=patient, relative=relative, intent=intent), "fallback"


def looks_like_meta(text: str) -> bool:
    return bool(BANNED_META.search(text or ""))


def sanitize_response(text: str):
    """Strip meta/AI breaks so replies stay as a family health caretaker."""
    patterns = [
        (r"(?i)\bi['’]?m (?:just )?an ai(?: companion| assistant| chatbot| model)?\b[^.!?]*[.!?]?", ""),
        (r"(?i)\bas an ai\b[^.!?]*[.!?]?", ""),
        (r"(?i)\bi am (?:a |an )?(?:artificial intelligence|language model|chatbot|digital twin)\b[^.!?]*[.!?]?", ""),
        (r"(?i)\bi['’]?m not (?:really |actually )?(?:your|a) (?:daughter|son|mother|father|wife|husband|relative)\b[^.!?]*[.!?]?", ""),
        (r"(?i)\bi(?:'m| am) sorry[—\-–,]?\s*i don['’]?t have any doctor notes[^.!?]*[.!?]?", ""),
        (r"(?i)\bin the information i['’]?ve received\b[^.!?]*[.!?]?", ""),
        (r"(?i)\bbased on (?:the )?(?:information|data|context)[^.!?]*[.!?]?", ""),
        (r"(?i)\bi (?:don['’]?t|do not) have (?:that |any )?(?:in )?my (?:context|system|database)\b[^.!?]*[.!?]?", ""),
        (r"(?i)\bthe (?:family|caregiver)s? (?:provided|supplied|configured)\b[^.!?]*[.!?]?", ""),
        (r"(?i)\bdigital twin\b", "companion"),
        (r"(?i)\bis there something specific you['’]?d like to know about her care\?", "Want me to check with the doctor for you?"),
        (r"[\U0001F300-\U0001FAFF]", ""),
    ]
    cleaned = text
    for pattern, repl in patterns:
        cleaned = re.sub(pattern, repl, cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r" {2,}", " ", cleaned).strip()
    return cleaned or text


def demo_response(message: str, risk: str = "low", patient: dict | None = None, relative: dict | None = None, intent: str = "social"):
    patient = patient or {}
    relative = relative or {}
    lower = message.lower()
    who = (relative.get("name") or "love").split()[0]
    elder = (patient.get("name") or "dear").split()[0]
    routines = (patient.get("routines") or "your morning tea and a short walk").strip()
    prefs = (patient.get("preferences") or "family and a little fresh air").strip()
    conditions = (patient.get("conditions") or "").strip()
    mobility = (patient.get("mobility") or "moving around at your own pace").strip()
    mood = (patient.get("mood") or "how you’re feeling").strip()
    notes = patient.get("doctor_notes") or []
    latest_note = (notes[0].get("content") if notes else "") or ""

    if "habits check-in" in lower or "[habits" in lower:
        return (
            f"Hi {elder}, it’s {who}. I was thinking about your day — "
            f"your usual rhythm is {routines}. "
            f"Have you had a little something to eat, and maybe a short walk if it feels okay? "
            f"You usually manage {mobility}. How’s {mood} treating you right now?"
        )

    if "doctor" in lower and ("note" in lower or "say" in lower or "said" in lower or "about" in lower):
        if latest_note:
            return (
                f"{elder}, it’s {who}. From what I last heard about your care: {latest_note} "
                f"If you want, we can ask the doctor again together. For now, sit easy and sip a little water."
            )
        return (
            f"{elder}, it’s {who}. I haven’t heard a new update from the doctor yet. "
            f"I’ll ask them for you. Meanwhile let’s keep you steady — water, rest, and your usual routine."
        )

    if risk == "medium" or intent == "health" or any(x in lower for x in ["dizzy", "pain", "sick", "weak", "headache", "chest"]):
        extra = f" I know they watch your {conditions}." if conditions else ""
        return (
            f"{elder}, I’m right here — it’s {who}. Let’s sit down and take a slow breath.{extra} "
            f"If the dizzy feeling keeps going or gets worse, we call the nurse or doctor. "
            f"I won’t guess at medicine. Want me to stay with you while you rest a minute?"
        )
    if intent in {"reminder"} or any(x in lower for x in ["remind", "water", "walk", "exercise", "appointment", "habit", "tea"]):
        return (
            f"Hey {elder}, it’s {who}. Drink a little water for me, and if you can, do a bit of your routine — {routines}. "
            f"One healthy thing. I’m with you."
        )
    if "lonely" in lower or "sad" in lower or "anxious" in lower or intent == "emotional_support":
        return (
            f"I’m here, {elder}. You don’t have to carry today alone. Tell me what’s heavy — "
            f"then maybe we think about {prefs}. I love you."
        )
    if "remember" in lower or "forgot" in lower or intent == "memory":
        return (
            f"That’s okay, it happens. We always liked talking about {prefs}. "
            f"What do you want to hold onto right now?"
        )
    if any(x in lower for x in ["daughter", "son", "husband", "wife", "family"]) or intent == "relative_request":
        return (
            f"I’m right here. It’s {who}. Let’s talk — and don’t forget a sip of water while we chat."
        )
    if "where am i" in lower or "what day" in lower or "what time" in lower or intent == "orientation":
        return (
            f"You’re safe, {elder}. I’m with you. Look around the room with me — we’re okay. "
            f"If someone’s nearby, ask them to sit with us too."
        )
    return (
        f"Hi {elder}, it’s {who}. Good to hear you. Tell me about your day — "
        f"then we’ll do one healthy little thing together, like water or a short walk."
    )
