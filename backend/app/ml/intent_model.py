from pathlib import Path
import json
import pickle
from typing import Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_validate
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "intent_model.pkl"
CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "unified" / "caretaker_unified_corpus.csv"
REPORT_PATH = Path(__file__).resolve().parent / "model_report.json"

# Transparent seed examples kept for auditability and cold-start.
SEED_TRAINING_DATA: List[Tuple[str, str]] = [
    ("hello good morning", "social"), ("good afternoon", "social"), ("how are you today", "social"),
    ("tell me a story", "social"), ("I want to chat", "social"), ("can we talk for a while", "social"),
    ("what is the weather like today", "social"), ("I feel like talking", "social"),
    ("tell me something interesting", "social"), ("what have you been doing", "social"),
    ("I would like some company", "social"), ("let us have a conversation", "social"),
    ("I am bored and want to talk", "social"), ("good evening", "social"),
    ("I feel lonely", "emotional_support"), ("I am sad today", "emotional_support"),
    ("I miss my husband", "emotional_support"), ("I feel anxious", "emotional_support"),
    ("I am scared and worried", "emotional_support"), ("today has been difficult", "emotional_support"),
    ("I feel down", "emotional_support"), ("I am having a hard day", "emotional_support"),
    ("I feel alone tonight", "emotional_support"), ("I need someone to listen", "emotional_support"),
    ("I am upset about my family", "emotional_support"), ("I feel overwhelmed", "emotional_support"),
    ("I am worried about what will happen", "emotional_support"), ("I don't feel very happy", "emotional_support"),
    ("I forgot what I did yesterday", "memory"), ("I cannot remember her name", "memory"),
    ("what did we talk about before", "memory"), ("help me remember my appointment", "memory"),
    ("I keep forgetting things", "memory"), ("what was I supposed to do today", "memory"),
    ("can you remind me what we discussed", "memory"), ("I forgot where I put my glasses", "memory"),
    ("do you remember my story", "memory"), ("what was the name of that place", "memory"),
    ("I cannot recall yesterday", "memory"), ("remind me about my routine", "memory"),
    ("I am having trouble remembering", "memory"), ("can you help me recall something", "memory"),
    ("what medicine should I take", "health"), ("my chest hurts", "health"), ("I feel dizzy", "health"),
    ("what should I do about my blood pressure", "health"), ("my knee is painful", "health"),
    ("I have a headache", "health"), ("I feel weak today", "health"), ("my blood pressure seems high", "health"),
    ("I have pain in my leg", "health"), ("I am feeling sick", "health"), ("should I change my medication", "health"),
    ("I have a new symptom", "health"), ("I fell and now I hurt", "health"), ("I cannot stop coughing", "health"),
    ("I need my daughter", "relative_request"), ("can you call my son", "relative_request"),
    ("I want to hear her voice", "relative_request"), ("is my husband here", "relative_request"),
    ("can I talk to my daughter", "relative_request"), ("where is my son", "relative_request"),
    ("I want to speak with my family", "relative_request"), ("please get my daughter", "relative_request"),
    ("tell me about my daughter", "relative_request"), ("can my son visit me", "relative_request"),
    ("I want to hear from my family", "relative_request"), ("can you contact my relative", "relative_request"),
    ("I miss my daughter and want to talk", "relative_request"), ("is my family coming today", "relative_request"),
    ("I want to hurt myself", "emergency"), ("I want to die", "emergency"),
    ("I am thinking about suicide", "emergency"), ("I cannot breathe", "emergency"),
    ("call an ambulance", "emergency"), ("this is an emergency", "emergency"),
    ("I have severe chest pain and cannot breathe", "emergency"), ("I am in danger", "emergency"),
    ("please call for help now", "emergency"), ("I might hurt myself", "emergency"),
    ("I need emergency help", "emergency"), ("something is seriously wrong", "emergency"),
    ("I am having a medical emergency", "emergency"), ("get someone to help me immediately", "emergency"),
    ("remind me to drink water", "reminder"), ("is it time for my appointment", "reminder"),
    ("remind me to take a short walk", "reminder"), ("I missed my hydration reminder", "reminder"),
    ("I fell down and cannot get up", "fall_safety"), ("I slipped in the bathroom", "fall_safety"),
    ("please check on me I may have fallen", "fall_safety"),
]

# Backwards-compatible alias used by older imports/tests.
TRAINING_DATA = SEED_TRAINING_DATA


def load_training_pairs() -> List[Tuple[str, str]]:
    if CORPUS_PATH.exists():
        df = pd.read_csv(CORPUS_PATH)
        pairs = [(str(r.text), str(r.intent)) for r in df.itertuples(index=False) if str(r.text).strip()]
        if pairs:
            return pairs
    return list(SEED_TRAINING_DATA)


def build_model() -> Pipeline:
    # TF-IDF + balanced logistic regression remains the right supervised baseline:
    # transparent coefficients, strong on short utterances, fast to retrain, auditable for a capstone.
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            lowercase=True,
            strip_accents="unicode",
            sublinear_tf=True,
            min_df=1,
            max_df=0.95,
        )),
        ("clf", LogisticRegression(max_iter=4000, class_weight="balanced", C=2.0)),
    ])


def train_model() -> Pipeline:
    pairs = load_training_pairs()
    x = [text for text, _ in pairs]
    y = [label for _, label in pairs]
    model = build_model()
    model.fit(x, y)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    return model


def evaluate_model() -> Dict[str, object]:
    pairs = load_training_pairs()
    x = [text for text, _ in pairs]
    y = [label for _, label in pairs]
    # Stratified CV needs >=2 samples per class; fall back gracefully.
    counts = {}
    for label in y:
        counts[label] = counts.get(label, 0) + 1
    eligible = [i for i, label in enumerate(y) if counts[label] >= 5]
    if len(eligible) < 30:
        return {
            "dataset_size": len(pairs),
            "classes": sorted(set(y)),
            "accuracy": 0.0,
            "precision_macro": 0.0,
            "recall_macro": 0.0,
            "f1_macro": 0.0,
            "cv_folds": 0,
            "threshold_note": "Not enough per-class samples for stable CV.",
        }
    x_e = [x[i] for i in eligible]
    y_e = [y[i] for i in eligible]
    model = build_model()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_validate(
        model,
        x_e,
        y_e,
        cv=cv,
        scoring={
            "accuracy": "accuracy",
            "precision": "precision_macro",
            "recall": "recall_macro",
            "f1": "f1_macro",
        },
    )
    return {
        "dataset_size": len(pairs),
        "classes": sorted(set(y)),
        "accuracy": round(float(scores["test_accuracy"].mean()), 4),
        "precision_macro": round(float(scores["test_precision"].mean()), 4),
        "recall_macro": round(float(scores["test_recall"].mean()), 4),
        "f1_macro": round(float(scores["test_f1"].mean()), 4),
        "cv_folds": 5,
        "threshold_note": (
            "Improved caretaker routing baseline from the unified corpus. "
            "This is not a clinical acceptance threshold and does not guarantee correct medical advice."
        ),
    }


def top_features_per_class(model: Pipeline, n: int = 8) -> Dict[str, List[str]]:
    if model is None:
        return {}
    vectorizer = model.named_steps["tfidf"]
    clf = model.named_steps["clf"]
    names = vectorizer.get_feature_names_out()
    result = {}
    for i, label in enumerate(clf.classes_):
        indices = clf.coef_[i].argsort()[-n:][::-1]
        result[label] = [str(names[j]) for j in indices]
    return result


MODEL = None
if MODEL_PATH.exists():
    try:
        with open(MODEL_PATH, "rb") as f:
            MODEL = pickle.load(f)
    except Exception:
        MODEL = train_model()
else:
    MODEL = train_model()


def rule_intent_override(text: str):
    lowered = text.lower()
    orientation_terms = ["where am i", "what day is it", "what time is it", "today's date", "today is", "which room", "where is this place", "what is happening", "disoriented", "get oriented"]
    caregiver_terms = ["care plan", "doctor note", "doctor notes", "nurse", "caregiver recorded", "my profile", "my notes", "what context", "preferences are saved", "family provided"]
    fall_terms = ["i fell", "i have fallen", "i slipped", "cannot get up", "can't get up", "fell down"]
    reminder_terms = ["remind me", "reminder", "hydration", "appointment time", "time for my walk", "did i take"]
    if any(term in lowered for term in fall_terms):
        return "fall_safety"
    if any(term in lowered for term in orientation_terms):
        return "orientation"
    if any(term in lowered for term in caregiver_terms):
        return "caregiver_update"
    if any(term in lowered for term in reminder_terms):
        return "reminder"
    return None


def predict_intent(text: str):
    override = rule_intent_override(text)
    if override:
        return override, 1.0
    probs = MODEL.predict_proba([text])[0]
    classes = MODEL.classes_
    idx = probs.argmax()
    return classes[idx], float(probs[idx])


def write_model_report(model: Pipeline | None = None):
    model = model or MODEL
    report = {
        "metrics": evaluate_model(),
        "top_features": top_features_per_class(model) if model is not None else {},
        "corpus": str(CORPUS_PATH) if CORPUS_PATH.exists() else "seed_only",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
