from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.db.repository import (
    add_message, add_note, add_suggestion, analytics, clear_messages, create_patient, create_relative,
    delete_note, delete_patient, delete_relative, get_patient, get_recent_messages,
    list_patients, list_suggestions, update_patient, update_relative,
)
from app.graph.workflow import GRAPH
from app.ml.intent_model import MODEL, evaluate_model, top_features_per_class
from app.models.schemas import (
    ChatRequest, ChatResponse, NoteCreate, PatientCreate, PatientUpdate,
    RelativeCreate, RelativeUpdate, SuggestionCreate,
)

router = APIRouter(prefix="/api")
AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "audio"


@router.get("/health")
def health():
    return {"status": "ok", "service": "behavioral-digital-twin", "model_loaded": MODEL is not None}

@router.get("/patients/{patient_id}")
def patient_detail(patient_id: int):
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@router.get("/patients")
def patients():
    return list_patients()


@router.post("/patients")
def patient(payload: PatientCreate):
    return create_patient(payload.model_dump())


@router.put("/patients/{patient_id}")
def patient_update(patient_id: int, payload: PatientUpdate):
    if not get_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return update_patient(patient_id, payload.model_dump())


@router.delete("/patients/{patient_id}")
def patient_delete(patient_id: int):
    if not delete_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"deleted": True}


@router.get("/patients/{patient_id}/messages")
def patient_messages(patient_id: int, limit: int = 40, user_role: str = "elderly"):
    if not get_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    role = user_role if user_role in {"elderly", "relative", "doctor"} else "elderly"
    return get_recent_messages(patient_id, max(1, min(limit, 100)), role)


@router.delete("/patients/{patient_id}/messages")
def patient_messages_clear(patient_id: int, user_role: str = "elderly"):
    if not get_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    role = user_role if user_role in {"elderly", "relative", "doctor"} else "elderly"
    deleted = clear_messages(patient_id, role)
    return {"deleted": deleted}


@router.get("/patients/{patient_id}/analytics")
def patient_analytics(patient_id: int):
    if not get_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return analytics(patient_id)


@router.post("/relatives")
def relative(payload: RelativeCreate):
    if not get_patient(payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return create_relative(payload.model_dump())


@router.put("/relatives/{relative_id}")
def relative_update(relative_id: int, payload: RelativeUpdate):
    if not get_patient(payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return update_relative(relative_id, payload.model_dump())


@router.delete("/relatives/{relative_id}")
def relative_delete(relative_id: int):
    if not delete_relative(relative_id):
        raise HTTPException(status_code=404, detail="Relative not found")
    return {"deleted": True}


@router.post("/notes")
def note(payload: NoteCreate):
    if payload.user_role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can add care notes")
    if not get_patient(payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return add_note(payload.patient_id, payload.author or "Doctor", payload.content)


@router.get("/patients/{patient_id}/suggestions")
def patient_suggestions(patient_id: int):
    if not get_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return list_suggestions(patient_id)


@router.post("/suggestions")
def suggestion(payload: SuggestionCreate):
    if payload.user_role not in {"relative", "elderly"}:
        raise HTTPException(status_code=403, detail="Only relatives or patients can suggest changes")
    if not get_patient(payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return add_suggestion(payload.patient_id, payload.author, payload.target, payload.content)


@router.delete("/notes/{note_id}")
def note_delete(note_id: int):
    if not delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"deleted": True}


@router.get("/ml/metrics")
def ml_metrics():
    return evaluate_model()


@router.get("/ml/features")
def ml_features():
    return top_features_per_class(MODEL)


@router.get("/ml/corpus")
def ml_corpus_summary():
    report = Path(__file__).resolve().parents[2] / "data" / "unified" / "corpus_build_report.json"
    if not report.exists():
        return {"status": "missing", "hint": "Run: python -m app.ml.build_unified_corpus"}
    import json
    return json.loads(report.read_text(encoding="utf-8"))


@router.get("/audio/{filename}")
def get_audio(filename: str):
    safe = Path(filename).name
    path = AUDIO_DIR / safe
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")
    media = "audio/wav" if path.suffix.lower() == ".wav" else "audio/aiff" if path.suffix.lower() == ".aiff" else "text/plain"
    return FileResponse(path, media_type=media, filename=safe)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    patient = get_patient(payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    role = payload.user_role if payload.user_role in {"elderly", "relative", "doctor"} else "elderly"
    opener = (payload.opener or "").strip().lower()
    if opener and opener not in {"habits"}:
        raise HTTPException(status_code=400, detail="Unknown opener")
    if not opener and not (payload.message or "").strip():
        raise HTTPException(status_code=400, detail="Message required")

    relative = None
    if payload.relative_id:
        relative = next((r for r in patient["relatives"] if r["id"] == payload.relative_id), None)
    if relative is None and patient["relatives"]:
        relative = patient["relatives"][0]

    history = get_recent_messages(payload.patient_id, user_role=role)

    if opener == "habits":
        # Internal cue for the graph/LLM — not shown as something the elder typed.
        message = (
            "[HABITS CHECK-IN] Start the conversation yourself. "
            "Warmly check on their day using their known routines, eating/preferences, "
            "mobility or walking, mood, and any care notes. "
            "Ask one gentle question. Short family sentences. No AI talk. No data dump."
        )
    else:
        message = payload.message.strip()
        add_message(payload.patient_id, "user", message, user_role=role)

    result = GRAPH.invoke({
        "patient": patient,
        "relative": relative,
        "message": message,
        "history": history,
        "user_role": role,
        "opener": opener,
    })

    add_message(
        payload.patient_id,
        "assistant",
        result["response"],
        result["intent"],
        result["risk_level"],
        role,
    )

    return ChatResponse(
        response=result["response"],
        intent=result["intent"],
        risk_level=result["risk_level"],
        confidence=result["confidence"],
        mode=result["mode"],
        policy=result.get("policy_name", ""),
        audio_url=result.get("audio_url"),
        audio_status=result.get("audio_status", ""),
        opener=opener,
    )
