from typing import Optional, TypedDict, Literal
from langgraph.graph import StateGraph, START, END

from app.ml.intent_model import predict_intent
from app.services.safety import assess_risk
from app.services.prompting import build_system_prompt
from app.services.llm import generate_response
from app.services.policy import policy_for_intent, policy_name_for_intent
from app.services.tts import synthesize_speech


class TwinState(TypedDict, total=False):
    patient: dict
    relative: Optional[dict]
    message: str
    history: list
    user_role: str
    opener: str
    intent: str
    confidence: float
    risk_level: str
    policy_name: str
    policy_text: str
    system_prompt: str
    response: str
    mode: str
    audio_url: Optional[str]
    audio_status: str


def safety_node(state: TwinState):
    if state.get("opener") == "habits":
        return {"risk_level": "low"}
    risk = assess_risk(state["message"])
    return {"risk_level": risk}


def classify_node(state: TwinState):
    if state.get("opener") == "habits":
        intent = "reminder"
        confidence = 0.95
        policy_name = policy_name_for_intent(intent)
        return {
            "intent": intent,
            "confidence": confidence,
            "policy_name": policy_name,
            "policy_text": policy_for_intent(intent),
        }
    intent, confidence = predict_intent(state["message"])
    if state.get("risk_level") == "critical":
        # Prefer emergency unless the utterance is clearly a fall safety case.
        if intent != "fall_safety":
            intent = "emergency"
        confidence = 1.0
    policy_name = policy_name_for_intent(str(intent))
    return {
        "intent": str(intent),
        "confidence": float(confidence),
        "policy_name": policy_name,
        "policy_text": policy_for_intent(str(intent)),
    }


def route_after_safety(state: TwinState) -> Literal["classify", "emergency_bypass"]:
    if state.get("risk_level") == "critical":
        return "emergency_bypass"
    return "classify"


def emergency_bypass_node(state: TwinState):
    intent, confidence = predict_intent(state["message"])
    if intent != "fall_safety":
        intent = "emergency"
    policy_name = policy_name_for_intent(intent)
    response, mode = generate_response(
        system_prompt="",
        message=state["message"],
        history=state.get("history", []),
        risk="critical",
        intent=intent,
        patient=state.get("patient") or {},
        relative=state.get("relative") or {},
    )
    return {
        "intent": intent,
        "confidence": 1.0 if confidence else 1.0,
        "policy_name": policy_name,
        "policy_text": policy_for_intent(intent),
        "response": response,
        "mode": mode,
        "system_prompt": "",
    }


def route_policy(state: TwinState) -> str:
    intent = state.get("intent", "social")
    mapping = {
        "emergency": "policy_emergency",
        "fall_safety": "policy_fall",
        "health": "policy_health",
        "reminder": "policy_reminder",
        "emotional_support": "policy_emotion",
        "memory": "policy_memory",
        "orientation": "policy_orientation",
        "relative_request": "policy_relative",
        "caregiver_update": "policy_caregiver",
        "social": "policy_social",
    }
    return mapping.get(intent, "policy_social")


def _policy_node(name: str):
    def _node(state: TwinState):
        return {
            "policy_name": name,
            "policy_text": policy_for_intent(state.get("intent", "social")),
        }
    _node.__name__ = f"apply_{name}"
    return _node


def context_node(state: TwinState):
    prompt = build_system_prompt(
        state["patient"],
        state.get("relative"),
        state["intent"],
        state["risk_level"],
        state["confidence"],
        state.get("user_role", "elderly"),
        state.get("history", []),
        policy_text=state.get("policy_text", ""),
        policy_name=state.get("policy_name", ""),
    )
    return {"system_prompt": prompt}


def generate_node(state: TwinState):
    response, mode = generate_response(
        system_prompt=state["system_prompt"],
        message=state["message"],
        history=state.get("history", []),
        risk=state["risk_level"],
        intent=state.get("intent", "social"),
        patient=state.get("patient") or {},
        relative=state.get("relative") or {},
    )
    return {"response": response, "mode": mode}


def speech_node(state: TwinState):
    relative = state.get("relative") or {}
    voice_hint = relative.get("voice_name") or ""
    audio = synthesize_speech(state.get("response", ""), voice_hint=voice_hint)
    return {
        "audio_url": audio.get("audio_url"),
        "audio_status": audio.get("status", "unknown"),
    }


builder = StateGraph(TwinState)
builder.add_node("safety", safety_node)
builder.add_node("emergency_bypass", emergency_bypass_node)
builder.add_node("classify", classify_node)

# Explicit care-aspect policy nodes (edges cover the full loop).
builder.add_node("policy_emergency", _policy_node("defer_to_human_emergency"))
builder.add_node("policy_fall", _policy_node("check_safety_and_notify"))
builder.add_node("policy_health", _policy_node("support_and_defer_clinical"))
builder.add_node("policy_reminder", _policy_node("gentle_cue_no_dosage"))
builder.add_node("policy_emotion", _policy_node("listen_validate_ground"))
builder.add_node("policy_memory", _policy_node("use_supplied_facts_only"))
builder.add_node("policy_orientation", _policy_node("simple_orientation_no_invention"))
builder.add_node("policy_relative", _policy_node("persona_relative_voice"))
builder.add_node("policy_caregiver", _policy_node("role_aware_status"))
builder.add_node("policy_social", _policy_node("warm_brief_company"))

builder.add_node("build_context", context_node)
builder.add_node("generate", generate_node)
builder.add_node("synthesize_speech", speech_node)

builder.add_edge(START, "safety")
builder.add_conditional_edges("safety", route_after_safety, {
    "emergency_bypass": "emergency_bypass",
    "classify": "classify",
})
builder.add_conditional_edges("classify", route_policy, {
    "policy_emergency": "policy_emergency",
    "policy_fall": "policy_fall",
    "policy_health": "policy_health",
    "policy_reminder": "policy_reminder",
    "policy_emotion": "policy_emotion",
    "policy_memory": "policy_memory",
    "policy_orientation": "policy_orientation",
    "policy_relative": "policy_relative",
    "policy_caregiver": "policy_caregiver",
    "policy_social": "policy_social",
})

for node in [
    "policy_emergency", "policy_fall", "policy_health", "policy_reminder",
    "policy_emotion", "policy_memory", "policy_orientation", "policy_relative",
    "policy_caregiver", "policy_social",
]:
    builder.add_edge(node, "build_context")

builder.add_edge("build_context", "generate")
builder.add_edge("generate", "synthesize_speech")
builder.add_edge("emergency_bypass", "synthesize_speech")
builder.add_edge("synthesize_speech", END)

GRAPH = builder.compile()
