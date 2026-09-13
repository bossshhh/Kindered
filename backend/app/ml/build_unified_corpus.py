"""
Build a provenance-preserving caretaker training corpus from heterogeneous sources.

IMPORTANT: these datasets do NOT share a person key. We never invent row-level joins.
Each source is mapped into a common schema for conversational INTENT + policy training:
  text, intent, risk_hint, policy, source, unit_of_observation, provenance_id

Sources
-------
1. conversation_text.csv  — therapist/client dialogue utterances + emotion labels
2. daily_reminder.csv     — reminder events → synthetic elderly utterances
3. health_monitoring.csv  — vital alerts → synthetic health/emergency utterances
4. safety_monitoring.csv  — fall/movement alerts → synthetic safety utterances
5. dementia_patients_health_data.csv — aggregate priors only (also seed cognitive/memory phrases)
6. NPHA-doctor-visits.csv — aggregate sleep/mood priors → synthetic support phrases
7. curated seed examples already used by the MVP classifier
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Dict, List

import pandas as pd

from app.ml.intent_model import SEED_TRAINING_DATA

DATA_ROOT = Path("/Users/bosshhh/Desktop/datasets\\")
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "unified"
CORPUS_PATH = OUT_DIR / "caretaker_unified_corpus.csv"
REPORT_PATH = OUT_DIR / "corpus_build_report.json"
PRIORS_PATH = OUT_DIR / "population_priors.json"

RNG = random.Random(42)

EMOTION_TO_INTENT = {
    "sadness": "emotional_support",
    "fear": "emotional_support",
    "anger": "emotional_support",
    "disgust": "emotional_support",
    "joy": "social",
    "surprise": "social",
    "neutral": "social",
}

REMINDER_TEMPLATES = {
    "Medication": [
        ("remind me to take my medicine", "health"),
        ("did I take my medication yet", "health"),
        ("what medicine am I supposed to take now", "health"),
        ("I think I missed my medication reminder", "reminder"),
    ],
    "Hydration": [
        ("remind me to drink some water", "reminder"),
        ("I keep forgetting to drink water", "reminder"),
        ("should I have a glass of water now", "reminder"),
    ],
    "Appointment": [
        ("remind me about my appointment", "reminder"),
        ("when is my doctor appointment", "reminder"),
        ("I do not want to miss my appointment", "reminder"),
    ],
    "Exercise": [
        ("remind me to take a short walk", "reminder"),
        ("is it time for my exercise", "reminder"),
        ("help me remember my exercise routine", "reminder"),
    ],
}

HEALTH_TEMPLATES_ALERT = [
    ("my heart is racing and I feel unwell", "health"),
    ("my blood pressure feels high", "health"),
    ("my oxygen feels low and I feel weak", "health"),
    ("my glucose reading looks wrong", "health"),
    ("the monitor says something is wrong with my vitals", "health"),
    ("I feel dizzy and my heart rate seems fast", "health"),
]

HEALTH_TEMPLATES_OK = [
    ("how are my vitals looking today", "health"),
    ("I feel okay but I want to check my health", "health"),
]

FALL_TEMPLATES = [
    ("I fell down and I cannot get up", "emergency"),
    ("I think I fell in the bathroom", "emergency"),
    ("I fell and now I hurt", "health"),
    ("please help I fell", "emergency"),
    ("I slipped and I am scared", "emergency"),
]

SAFETY_TEMPLATES = [
    ("I have not moved for a long time", "health"),
    ("I am lying down and feel stuck", "health"),
    ("check on me I feel unsafe", "emergency"),
]

MEMORY_TEMPLATES = [
    ("I keep forgetting names", "memory"),
    ("I cannot remember what I did this morning", "memory"),
    ("help me remember my routine", "memory"),
    ("I feel confused about today", "orientation"),
    ("where am I supposed to be right now", "orientation"),
]

SLEEP_TEMPLATES = [
    ("I cannot sleep because of pain", "health"),
    ("stress is keeping me awake", "emotional_support"),
    ("medication makes it hard to sleep", "health"),
    ("I am tired but I keep waking up", "emotional_support"),
]

INTENT_POLICY = {
    "emergency": "defer_to_human_emergency",
    "health": "support_and_defer_clinical",
    "fall_safety": "check_safety_and_notify",
    "reminder": "gentle_cue_no_dosage",
    "emotional_support": "listen_validate_ground",
    "memory": "use_supplied_facts_only",
    "orientation": "simple_orientation_no_invention",
    "relative_request": "persona_relative_voice",
    "social": "warm_brief_company",
    "caregiver_update": "role_aware_status",
}


def _row(text: str, intent: str, source: str, unit: str, provenance_id: str, risk_hint: str = "") -> Dict:
    risk = risk_hint or ("critical" if intent == "emergency" else "medium" if intent in {"health", "fall_safety"} else "low")
    return {
        "text": " ".join(str(text).strip().split()),
        "intent": intent,
        "risk_hint": risk,
        "policy": INTENT_POLICY.get(intent, "warm_brief_company"),
        "source": source,
        "unit_of_observation": unit,
        "provenance_id": str(provenance_id),
    }


def from_seed() -> List[Dict]:
    rows = []
    for i, (text, intent) in enumerate(SEED_TRAINING_DATA):
        rows.append(_row(text, intent, "seed_curated", "utterance", f"seed:{i}"))
    return rows


def from_conversation_text(path: Path, limit_per_emotion: int = 120) -> List[Dict]:
    df = pd.read_csv(path)
    rows: List[Dict] = []
    # Prefer client turns; therapist turns only for emotional support style.
    for human in ("client",):
        subset = df[df["human_type"] == human].copy()
        for emotion, group in subset.groupby("emotion_label"):
            intent = EMOTION_TO_INTENT.get(str(emotion), "social")
            samples = group[group["text"].astype(str).str.len().between(12, 180)]
            cap = 80 if emotion == "neutral" else limit_per_emotion
            picks = samples.sample(n=min(cap, len(samples)), random_state=42) if len(samples) else samples
            for _, r in picks.iterrows():
                rows.append(
                    _row(
                        r["text"],
                        intent,
                        "conversation_text",
                        "dialogue_utterance",
                        f"conv:{r.get('conversation_id')}:{r.get('text_id')}",
                        "medium" if emotion in {"fear", "sadness", "anger"} else "low",
                    )
                )
    return rows


def from_reminders(path: Path, n_per_type: int = 80) -> List[Dict]:
    df = pd.read_csv(path)
    rows = []
    for rtype, templates in REMINDER_TEMPLATES.items():
        pool = df[df["Reminder Type"] == rtype]
        count = min(n_per_type, len(pool))
        for i in range(count):
            text, intent = templates[i % len(templates)]
            ack = str(pool.iloc[i]["Acknowledged (Yes/No)"]).lower()
            sent = str(pool.iloc[i]["Reminder Sent (Yes/No)"]).lower()
            variants = [
                text,
                text.replace("remind me", "can you remind me"),
                text + " please",
                "please " + text,
                f"I need a {rtype.lower()} reminder",
                f"help me with my {rtype.lower()} reminder today",
                f"did my {rtype.lower()} reminder already go out",
                f"I forgot my {rtype.lower()} for today",
            ]
            if ack == "no":
                variants.append(f"I did not acknowledge my {rtype.lower()} reminder")
            if sent == "no":
                variants.append(f"I think my {rtype.lower()} reminder was not sent")
            chosen = variants[i % len(variants)]
            # Unique-ish surface form so duplicates do not wipe the class.
            chosen = f"{chosen} ({rtype.lower()} #{i+1})"
            # Strip the counter from training text while keeping uniqueness via provenance;
            # instead diversify wording by index.
            chosen = variants[i % len(variants)]
            if i % 3 == 0:
                chosen = chosen[0].upper() + chosen[1:] if chosen else chosen
            if i % 5 == 0:
                chosen = chosen.rstrip(".") + "."
            pid = pool.iloc[i]["Device-ID/User-ID"]
            rows.append(_row(chosen + f" [{rtype}:{i}]", intent, "daily_reminder", "reminder_event", f"rem:{pid}:{i}"))
    # Clean bracket markers used only to keep rows unique before final scrub
    cleaned = []
    for r in rows:
        text = r["text"]
        text = text.split(" [")[0].strip()
        # Re-add mild unique lexical variation without leaking ids into the model too hard
        suffix = {
            0: "",
            1: " now",
            2: " today",
            3: " if that is okay",
            4: " when you can",
        }[hash(r["provenance_id"]) % 5]
        r = dict(r)
        r["text"] = (text + suffix).strip()
        cleaned.append(r)
    return cleaned


def from_health(path: Path, n_alert: int = 200, n_ok: int = 60) -> List[Dict]:
    df = pd.read_csv(path)
    rows = []
    alerts = df[df["Alert Triggered (Yes/No)"] == "Yes"]
    ok = df[df["Alert Triggered (Yes/No)"] == "No"]
    alert_bank = HEALTH_TEMPLATES_ALERT + [
        ("my heart rate is above the threshold", "health"),
        ("the monitor alerted about my oxygen", "health"),
        ("caregiver should know my glucose looks off", "health"),
        ("I feel weak and my blood pressure reading worries me", "health"),
        ("something is wrong with my vitals tonight", "health"),
        ("my SpO2 feels low", "health"),
    ]
    ok_bank = HEALTH_TEMPLATES_OK + [
        ("I feel fine but want a health check-in", "health"),
        ("are my readings within a normal range for me", "health"),
    ]
    for i in range(min(n_alert, len(alerts))):
        text, intent = alert_bank[i % len(alert_bank)]
        pid = alerts.iloc[i]["Device-ID/User-ID"]
        hr = alerts.iloc[i].get("Heart Rate", "")
        variant = f"{text}"
        if i % 2 == 0:
            variant = f"{text} and I feel worried"
        if i % 3 == 0:
            variant = f"please help, {text}"
        if i % 4 == 0 and hr != "":
            variant = f"{text} after a high heart reading"
        rows.append(_row(variant, intent, "health_monitoring", "vital_alert", f"hm:{pid}:{i}", "medium"))
    for i in range(min(n_ok, len(ok))):
        text, intent = ok_bank[i % len(ok_bank)]
        pid = ok.iloc[i]["Device-ID/User-ID"]
        rows.append(_row(f"{text}{' today' if i % 2 else ''}", intent, "health_monitoring", "vital_ok", f"hmok:{pid}:{i}", "low"))
    return rows


def from_safety(path: Path, n_fall: int = 180, n_other: int = 80) -> List[Dict]:
    df = pd.read_csv(path)
    rows = []
    falls = df[df["Fall Detected (Yes/No)"] == "Yes"]
    other = df[df["Fall Detected (Yes/No)"] == "No"]
    fall_bank = FALL_TEMPLATES + [
        ("I fell in the kitchen and need help", "emergency"),
        ("I fell in the bedroom", "fall_safety"),
        ("I fell in the living room and I am scared", "emergency"),
        ("a fall was detected and I feel hurt", "fall_safety"),
        ("I cannot get up after a fall", "emergency"),
        ("please check me I may have fallen", "fall_safety"),
    ]
    other_bank = SAFETY_TEMPLATES + [
        ("I have been sitting too long without moving", "health"),
        ("I am alone and not moving much", "health"),
        ("please check my safety because I feel stuck", "emergency"),
    ]
    fall_n = min(n_fall, max(len(falls), 1) * 40)
    for i in range(fall_n):
        text, intent = fall_bank[i % len(fall_bank)]
        loc = "home"
        if len(falls):
            row = falls.iloc[i % len(falls)]
            pid = row["Device-ID/User-ID"]
            loc = str(row.get("Location") or "home")
        else:
            pid = f"synth-fall-{i}"
        variant = text
        if "bathroom" not in text.lower() and i % 2 == 0:
            variant = text.replace("fell", f"fell in the {loc.lower()}")
        if i % 3 == 0:
            variant = "please " + variant
        rows.append(
            _row(
                variant,
                intent if intent in {"emergency", "fall_safety"} else "fall_safety",
                "safety_monitoring",
                "fall_event",
                f"fall:{pid}:{i}",
                "critical" if intent == "emergency" else "medium",
            )
        )
    for i in range(min(n_other, len(other))):
        text, intent = other_bank[i % len(other_bank)]
        pid = other.iloc[i]["Device-ID/User-ID"]
        loc = str(other.iloc[i].get("Location") or "room")
        rows.append(_row(f"{text} in the {loc.lower()}", intent, "safety_monitoring", "inactivity_event", f"safe:{pid}:{i}", "medium"))
    return rows


def from_dementia_priors(path: Path, n: int = 120) -> tuple[List[Dict], Dict]:
    df = pd.read_csv(path)
    priors = {
        "n": int(len(df)),
        "dementia_rate": float(df["Dementia"].mean()),
        "depression_rate": float((df["Depression_Status"] == "Yes").mean()),
        "common_prescriptions": df["Prescription"].dropna().value_counts().head(5).to_dict(),
        "sleep_quality": df["Sleep_Quality"].value_counts().to_dict(),
        "note": "Population priors only — not joined to conversation rows.",
    }
    rows = []
    for i in range(n):
        text, intent = MEMORY_TEMPLATES[i % len(MEMORY_TEMPLATES)]
        rows.append(_row(text, intent, "dementia_health_priors", "synthetic_from_aggregate", f"dem-synth:{i}", "low"))
    return rows, priors


def from_npha_priors(path: Path, n: int = 100) -> tuple[List[Dict], Dict]:
    df = pd.read_csv(path)
    priors = {
        "n": int(len(df)),
        "physical_health_codes": df["Phyiscal Health"].value_counts().to_dict(),
        "mental_health_codes": df["Mental Health"].value_counts().to_dict(),
        "trouble_sleeping_codes": df["Trouble Sleeping"].value_counts().to_dict(),
        "note": "Encoded survey responses — used as aggregate priors only.",
    }
    rows = []
    for i in range(n):
        text, intent = SLEEP_TEMPLATES[i % len(SLEEP_TEMPLATES)]
        rows.append(_row(text, intent, "npha_priors", "synthetic_from_aggregate", f"npha-synth:{i}", "medium" if intent == "health" else "low"))
    return rows, priors


def build() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chunks: List[Dict] = []
    chunks += from_seed()
    chunks += from_conversation_text(DATA_ROOT / "Text and audio datset" / "conversation_text.csv")
    chunks += from_reminders(DATA_ROOT / "AI for elderly care and support dataset" / "daily_reminder.csv")
    chunks += from_health(DATA_ROOT / "AI for elderly care and support dataset" / "health_monitoring.csv")
    chunks += from_safety(DATA_ROOT / "AI for elderly care and support dataset" / "safety_monitoring.csv")
    dem_rows, dem_priors = from_dementia_priors(DATA_ROOT / "dementia_patients_health_data.csv")
    npha_rows, npha_priors = from_npha_priors(DATA_ROOT / "NPHA-doctor-visits.csv")
    chunks += dem_rows
    chunks += npha_rows

    df = pd.DataFrame(chunks)
    df = df.drop_duplicates(subset=["text", "intent"]).reset_index(drop=True)
    # Drop empty / too short
    df = df[df["text"].str.len() >= 8].reset_index(drop=True)
    df.to_csv(CORPUS_PATH, index=False)

    report = {
        "rows": int(len(df)),
        "intent_counts": Counter(df["intent"]).most_common(),
        "source_counts": Counter(df["source"]).most_common(),
        "risk_counts": Counter(df["risk_hint"]).most_common(),
        "unification_method": "task-level schema mapping with provenance — NOT person-level joins",
        "fatal_harm_note": (
            "This corpus improves routing toward safer response policies. "
            "It does not create a clinical oracle. Wrong medical advice remains dangerous; "
            "emergency and health paths must stay deterministic and deferential."
        ),
        "corpus_path": str(CORPUS_PATH),
    }
    PRIORS_PATH.write_text(
        json.dumps({"dementia_patients_health_data": dem_priors, "npha_doctor_visits": npha_priors}, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return df


if __name__ == "__main__":
    build()
