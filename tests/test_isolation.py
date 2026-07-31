"""Prep data must never reach student-facing output."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

sys.path.insert(0, str(ROOT))
import icsutil

STUDENT_FILES = ["index.html", "calendar.ics", "calendar.json"]
PREP_MARKERS = ["Prep starts", "Arrives", "prep-inv", "Lab Prep",
                "Order: Investigation", '"prep"', "prep:"]


class TestPrepIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [sys.executable, "build.py"], cwd=ROOT,
            capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    def test_prep_outputs_exist(self):
        self.assertTrue((DOCS / "prep.html").exists())
        self.assertTrue((DOCS / "prep.ics").exists())

    def test_no_prep_marker_appears_in_student_output(self):
        for name in STUDENT_FILES:
            text = (DOCS / name).read_text(encoding="utf-8")
            for marker in PREP_MARKERS:
                self.assertNotIn(
                    marker, text,
                    f"{marker!r} leaked into docs/{name}")

    def test_student_ics_event_count_is_unchanged(self):
        text = (DOCS / "calendar.ics").read_text(encoding="utf-8")
        self.assertEqual(text.count("BEGIN:VEVENT"), 102)

    def test_prep_ics_is_structurally_valid(self):
        self.assertEqual(icsutil.verify_ics(DOCS / "prep.ics"), [])

    def test_rebuild_is_idempotent(self):
        before = {n: (DOCS / n).read_bytes()
                  for n in STUDENT_FILES + ["prep.html", "prep.ics"]}
        result = subprocess.run([sys.executable, "build.py"], cwd=ROOT,
                                capture_output=True, text=True)
        # Assert the rebuild actually succeeded. Without this the test passes
        # when build.py crashes on startup: nothing gets rewritten, so every
        # byte comparison below trivially holds.
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, content in before.items():
            self.assertEqual((DOCS / name).read_bytes(), content,
                             f"docs/{name} was rewritten with no change")


if __name__ == "__main__":
    unittest.main()
