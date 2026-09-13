import json
from pathlib import Path

from app.ml.build_unified_corpus import build as build_corpus
from app.ml.intent_model import evaluate_model, top_features_per_class, train_model, write_model_report

if __name__ == "__main__":
    print("Building unified caretaker corpus…")
    corpus = build_corpus()
    print(f"Corpus rows: {len(corpus)}")
    print("Training supervised intent model…")
    model = train_model()
    report = write_model_report(model)
    print(json.dumps(report, indent=2))
    print("Done. Model + report written under backend/app/ml/")
