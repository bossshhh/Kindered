# Behavioral Digital Twin — Kindred MVP

A capstone-ready MVP for an elderly-focused conversational companion. The repository contains the FastAPI backend and React/Vite frontend in one project.

## What is implemented

### Product

- Kindred elderly-first landing experience
- Three-step scroll journey: Meet Kindred → Share a thought → Start talking
- Seamless landing-message → companion handoff
- Conversational UI with persistent local history
- Context view grounded in the stored patient/relative profile
- Browser speech recognition and speech synthesis
- Browser voice selection and replay
- Relative persona management
- Patient create/edit/delete
- Relative create/edit/delete
- Care note create/delete
- Observed analytics from SQLite instead of fake dashboard numbers
- Demo role switch for elderly / relative / doctor experiences

### Backend

- FastAPI
- SQLite with foreign-key enforcement
- LangGraph StateGraph orchestration
- Groq integration with local demo/fallback mode
- Deterministic emergency safety gate before generation
- Health-sensitive generation policy
- Structured patient/relative context
- Conversation history
- Analytics endpoints

### ML

- Transparent supervised baseline: TF-IDF + Logistic Regression
- Unified multi-source caretaker corpus with provenance (task-level merge, not person joins)
- Classes include social, emotional_support, memory, health, relative_request, emergency, reminder, fall_safety, orientation
- 5-fold stratified cross-validation
- Deterministic safety gate + LangGraph policy routing before generation
- Response text stored and converted to local audio (`/api/audio/...`)

See `docs/ML_AND_DATASET_NOTES.md` for the dataset unification method and limits.

## Architecture

```text
User message
    ↓
Intent classifier + deterministic risk gate
    ↓
Patient / relative / authorized context
    ↓
LangGraph
  classify
      ↓
  build_context
      ↓
  generate
    ↓
Groq LLM OR local demo/fallback
    ↓
Response validation / identity guardrail
    ↓
SQLite conversation history
    ↓
Text + optional browser speech
```

## Important research framing

The system is a **grounded conversational companion prototype**, not a clinical digital twin and not a system that can guarantee zero hallucinations.

The original brief asked for zero hallucinations. That is not a defensible engineering claim. The implementation instead uses explicit source hierarchy, controlled context, deterministic safety gates, conservative generation settings and a fallback response layer to reduce unsupported output.

The AI must not falsely claim to literally be a deceased or real relative.

## ML / dataset decision

The original brief proposed merging four elderly-care/health datasets row-for-row. That is not scientifically defensible unless the sources share a real entity key and compatible units of observation. Survey respondents, speech utterances, clinical records and conversation examples are different entities.

The current MVP therefore keeps the supervised intent dataset separate from patient-specific context. See `docs/ML_AND_DATASET_NOTES.md` for the rationale and recommended future datasets.

## Run locally

### Backend

From the repository root:

```bash
./run_backend.sh
```

Backend:

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health
- ML metrics: http://127.0.0.1:8000/api/ml/metrics

The default `.env.example` is configured for demo mode. Copy it to `backend/.env`.

For Groq:

```env
GROQ_API_KEY=your_real_key
DEMO_MODE=false
GROQ_MODEL=llama-3.3-70b-versatile
```

### Frontend

```bash
./run_frontend.sh
```

Vite normally serves:

http://localhost:5173/app/

### Production-style local build

```bash
cd frontend
npm install
npm run build
cd ..
./run_backend.sh
```

FastAPI serves the resulting `frontend/dist` at `/app`.

## Presentation demo flow

1. Open `/app/`.
2. Show the calm Kindred landing experience.
3. Enter a sentence in **Share a thought**.
4. Press **Begin conversation**.
5. Show the message arriving in Companion automatically.
6. Explain: intent → safety → context → LangGraph → Groq/demo → persistence.
7. Switch to the relative/doctor demo role.
8. Show patient + persona configuration.
9. Show the real conversation analytics.
10. Open the System page to explain guardrails and limitations.

## Limitations to say explicitly during the presentation

- The intent model is a small supervised baseline.
- The model is not a medical classifier.
- Analytics describe application behavior; they do not diagnose health conditions.
- Browser speech is used for the MVP; real-person voice cloning is not part of this implementation.
- The role switch is a demo control, not production authentication.
- Production deployment would require authentication, authorization, consent, audit logging, encryption, stronger evaluation and clinical/safety review.
# Kindered
# Kindered
