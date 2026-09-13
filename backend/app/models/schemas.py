from typing import Optional
from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=1, le=120)
    gender: str = ""
    marital_status: str = ""
    mood: str = ""
    conditions: str = ""
    allergies: str = ""
    mobility: str = ""
    behavioral_traits: str = ""
    preferences: str = ""
    routines: str = ""
    notes: str = ""


class PatientUpdate(PatientCreate):
    pass


class RelativeCreate(BaseModel):
    patient_id: int
    name: str = Field(min_length=1, max_length=120)
    age: Optional[int] = Field(default=None, ge=1, le=120)
    gender: str = ""
    relationship: str = ""
    personality: str = ""
    communication_style: str = ""
    preferences: str = ""
    memories: str = ""
    voice_name: str = ""


class RelativeUpdate(RelativeCreate):
    pass


class NoteCreate(BaseModel):
    patient_id: int
    author: str = "Doctor"
    content: str = Field(min_length=1, max_length=5000)
    user_role: str = "doctor"


class SuggestionCreate(BaseModel):
    patient_id: int
    author: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=5000)
    user_role: str = "relative"


class ChatRequest(BaseModel):
    patient_id: int
    relative_id: Optional[int] = None
    message: str = Field(default="", max_length=2000)
    user_role: str = "elderly"
    # "habits" = caretaker opens from routines / eating / mobility / mood (no user bubble)
    opener: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    risk_level: str
    confidence: float
    mode: str
    policy: str = ""
    audio_url: Optional[str] = None
    audio_status: str = ""
    opener: str = ""


class VoiceSettings(BaseModel):
    voice_name: str = ""
