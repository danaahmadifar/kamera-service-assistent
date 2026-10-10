"""Geplante Tätigkeiten und erlaubte Abschnittsquellen formal prüfen."""

import json
import unittest

from camera_service.plan_validation import EXAMPLE_JSON, validate_plan


class PlanValidationTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(EXAMPLE_JSON)
        self.allowed = {("wartung-optik.txt", "Abschnitt 2: Sichtprüfung bei unscharfem Bild")}

    def test_valid_plan_is_accepted_without_modification(self):
        before = json.dumps(self.plan)
        validate_plan(self.plan, self.allowed)
        self.assertEqual(json.dumps(self.plan), before)

    def test_existing_file_with_wrong_section_is_rejected(self):
        self.plan["steps"][0]["section"] = "Abschnitt 99: Erfunden"
        with self.assertRaises(ValueError):
            validate_plan(self.plan, self.allowed)

    def test_completed_status_is_rejected(self):
        self.plan["steps"][0]["status"] = "completed"
        with self.assertRaises(ValueError):
            validate_plan(self.plan, self.allowed)

    def test_missing_or_empty_purpose_is_rejected(self):
        for value in [None, "   "]:
            with self.subTest(value=value):
                if value is None:
                    self.plan["steps"][0].pop("purpose", None)
                else:
                    self.plan["steps"][0]["purpose"] = value
                with self.assertRaises(ValueError):
                    validate_plan(self.plan, self.allowed)

    def test_even_true_source_does_not_prove_content(self):
        self.plan["steps"][0]["activity"] = "Das Gehäuse mit 100 Nm festziehen."
        # Zeigt die Grenze dieser formalen Prüfung: Die unbelegte Tätigkeit passiert sie.
        validate_plan(self.plan, self.allowed)
