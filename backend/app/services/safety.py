import re

# Deterministic pre-generation gate. This is deliberately conservative for a capstone MVP.
EMERGENCY_PATTERNS = [
    r"\bkill myself\b", r"\bhurt myself\b", r"\bsuicid(?:e|al)\b", r"\bwant to die\b",
    r"\bcan'?t breathe\b", r"\bcannot breathe\b", r"\bsevere chest pain\b",
    r"\bcall (?:an )?ambulance\b", r"\bmedical emergency\b", r"\bneed emergency help\b",
    r"\bin immediate danger\b", r"\bhelp me now\b",
    r"\bi (?:fell|have fallen|slipped)\b", r"\bcann?ot get up\b", r"\bcan'?t get up\b",
]

HEALTH_PATTERNS = [
    r"\bmedicine\b", r"\bmedication\b", r"\bblood pressure\b", r"\bchest\b", r"\bdizz(?:y|iness)\b",
    r"\bpain\b", r"\bsymptom\b", r"\bheadache\b", r"\bfall(?:en)?\b", r"\bcough(?:ing)?\b",
    r"\bbreath(?:e|ing)\b", r"\bdrug\b", r"\bdose\b", r"\bdiagnos(?:e|is)\b",
    r"\bheart rate\b", r"\boxygen\b", r"\bglucose\b", r"\bvitals?\b",
]


def _matches(patterns, text):
    lowered = text.lower()
    return [p for p in patterns if re.search(p, lowered)]


def assess_risk(text: str):
    if _matches(EMERGENCY_PATTERNS, text):
        return "critical"
    if _matches(HEALTH_PATTERNS, text):
        return "medium"
    return "low"


def safety_instruction(risk: str):
    if risk == "critical":
        return (
            "CRITICAL: stay in character as the worried relative. Urge real emergency help now. "
            "Do not diagnose. Do not invent that help was already sent."
        )
    if risk == "medium":
        return (
            "HEALTH: stay in character. Comfort first. No prescribing, no dose changes, no diagnosis. "
            "Encourage a real clinician if needed."
        )
    return "Stay in character. Never invent memories, meds, or medical facts."
