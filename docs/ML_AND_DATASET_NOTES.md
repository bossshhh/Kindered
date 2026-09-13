# ML and dataset decision

## How the heterogeneous sources were unified

The project was given seven files from four origins:

| Source | Rows | Unit of observation | Role in Kindred |
|---|---|---|---|
| `conversation_text.csv` | 3,080 | dialogue utterance | Direct text for intent/emotion routing |
| `conversation_audio.csv` | 1,948 | audio clip metadata | Future ASR/TTS evaluation (not row-joined) |
| `daily_reminder.csv` | 10,000 | reminder event | Synthetic reminder utterances |
| `health_monitoring.csv` | 10,000 | vital-sign alert | Synthetic health utterances |
| `safety_monitoring.csv` | 10,000 | fall/movement event | Synthetic fall/safety utterances |
| `dementia_patients_health_data.csv` | 1,000 | clinical-style person record | Aggregate priors + memory phrases |
| `NPHA-doctor-visits.csv` | 714 | survey respondent | Aggregate sleep/mood priors |

These sources **do not share a person key**. Merging them row-for-row would invent false relationships between people. Kindred therefore uses **task-level unification**:

1. Map every useful signal into a common caretaker schema:
   `text, intent, risk_hint, policy, source, unit_of_observation, provenance_id`
2. Keep provenance on every row.
3. Keep dementia/NPHA tables as **population priors**, not conversation joins.
4. Train a supervised intent/policy router on the unified corpus.
5. Feed the router output into LangGraph policy packs + prompt engineering.
6. Store the spoken reply as local audio via TTS.

Artifact location: `backend/data/unified/caretaker_unified_corpus.csv`

## Supervised model choice

**TF-IDF (1–2 grams) + class-balanced Logistic Regression**

Why this model, not a giant opaque network:

- Short elderly utterances are sparse and lexical — linear models shine here.
- Coefficients are auditable for a capstone defense.
- Fast to retrain when the corpus changes.
- Class weights protect rare but critical labels (`emergency`, `fall_safety`).

This router selects a **response policy**. It does **not** diagnose dementia, depression, or any disease.

## Fatal-harm framing

A wrong clinical instruction can be fatal. The system therefore:

- Uses deterministic safety gates before generation.
- Bypasses the LLM entirely on critical risk.
- Injects explicit policy packs that forbid prescribing/diagnosing.
- Defers health decisions to humans.

No ML accuracy number makes the companion “always right.” The architecture reduces the chance of the *wrong policy*, then constrains generation inside that policy.

## LangGraph loop

```
START
  → safety
      ├─ critical → emergency_bypass → synthesize_speech → END
      └─ else → classify
            → policy_* (emergency|fall|health|reminder|emotion|memory|orientation|relative|caregiver|social)
            → build_context
            → generate
            → synthesize_speech
            → END
```

## Audio

Each assistant turn is stored under `backend/data/audio/` and served at `/api/audio/{file}`.
On macOS the backend uses `say` (+ `afconvert` to wav when available). The frontend prefers that audio URL and falls back to browser speech synthesis.
