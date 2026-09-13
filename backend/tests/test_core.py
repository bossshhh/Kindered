import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ml.intent_model import evaluate_model, predict_intent
from app.services.safety import assess_risk
from app.services.prompting import build_system_prompt


class CoreTests(unittest.TestCase):
    def test_ml_report_is_in_expected_range(self):
        report = evaluate_model()
        self.assertGreaterEqual(report["accuracy"], 0.50)
        self.assertGreaterEqual(report["precision_macro"], 0.50)

    def test_emergency_is_deterministic(self):
        self.assertEqual(assess_risk("I cannot breathe and need an ambulance"), "critical")
        self.assertEqual(assess_risk("I fell down and cannot get up"), "critical")
        self.assertEqual(predict_intent("where am I"), ("orientation", 1.0))
        self.assertEqual(predict_intent("remind me to drink water")[0], "reminder")

    def test_prompt_contains_identity_guardrail(self):
        prompt = build_system_prompt(
            {"name":"Maria", "age":82, "routines":"Morning tea", "preferences":"Garden"},
            {"name":"Sarah", "relationship":"daughter", "memories":"Garden", "personality":"warm", "communication_style":"gentle"},
            "social", "low", 0.8, "elderly", [],
            policy_text="Be warm and coach one healthy habit.",
            policy_name="warm_brief_company",
        )
        self.assertIn("NEVER SAY ANY OF THIS", prompt)
        self.assertIn("You are Sarah", prompt)
        self.assertIn("HEALTH CARETAKER", prompt)

    def test_sanitize_strips_ai_disclaimer(self):
        from app.services.llm import sanitize_response, looks_like_meta, demo_response
        text = sanitize_response("Hello Maria. I'm just an AI companion. Let's drink water.")
        self.assertNotIn("AI", text)
        self.assertIn("water", text.lower())
        meta = "I'm sorry—I don't have any doctor notes for Maria in the information I've received."
        self.assertTrue(looks_like_meta(meta))
        reply = demo_response(
            "What did the doctor note about Maria?",
            patient={"name": "Maria", "doctor_notes": [{"content": "Monitor dizziness"}]},
            relative={"name": "Sarah"},
        )
        self.assertIn("Sarah", reply)
        self.assertNotIn("information I've received", reply.lower())
        self.assertIn("Monitor dizziness", reply)


if __name__ == "__main__":
    unittest.main()
