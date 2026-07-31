import unittest
from pathlib import Path
import tempfile

import icsutil


class TestIcsEscape(unittest.TestCase):
    def test_escapes_the_four_special_characters(self):
        self.assertEqual(icsutil.ics_escape("a,b"), "a\\,b")
        self.assertEqual(icsutil.ics_escape("a;b"), "a\\;b")
        self.assertEqual(icsutil.ics_escape("a\\b"), "a\\\\b")
        self.assertEqual(icsutil.ics_escape("a\nb"), "a\\nb")

    def test_backslash_is_escaped_before_the_others(self):
        # If order were wrong, "\," would become "\\\\," instead of "\\\\\\,".
        self.assertEqual(icsutil.ics_escape("\\,"), "\\\\\\,")


class TestFold(unittest.TestCase):
    def test_short_line_is_untouched(self):
        self.assertEqual(icsutil.fold("SUMMARY:short"), ["SUMMARY:short"])

    def test_long_line_folds_with_leading_space(self):
        out = icsutil.fold("SUMMARY:" + "x" * 200)
        self.assertGreater(len(out), 1)
        for part in out[1:]:
            self.assertTrue(part.startswith(" "))

    def test_every_physical_line_fits_in_75_octets(self):
        out = icsutil.fold("SUMMARY:" + "é" * 200)
        for part in out:
            self.assertLessEqual(len(part.encode("utf-8")), 75)


class TestSlug(unittest.TestCase):
    def test_lowercases_and_replaces_punctuation(self):
        self.assertEqual(icsutil.slug("INV-8", "6.8"), "inv-8-6-8")

    def test_drops_empty_parts(self):
        self.assertEqual(icsutil.slug("unit-2", None, "2.7"), "unit-2-2-7")


class TestCalendarHeader(unittest.TestCase):
    def test_escapes_delimiters_in_both_name_fields(self):
        out = icsutil.calendar_header("AP Biology, Honors; P3", "lab prep")
        joined = "\n".join(out)
        self.assertIn("AP Biology\\, Honors\\; P3", joined)
        self.assertNotIn("AP Biology, Honors; P3", joined)

    def test_folds_a_long_name(self):
        out = icsutil.calendar_header("X" * 200, "lab prep")
        for line in out:
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_starts_with_begin_and_version(self):
        out = icsutil.calendar_header("AP Biology", "lab prep")
        self.assertEqual(out[0], "BEGIN:VCALENDAR")
        self.assertEqual(out[1], "VERSION:2.0")


class TestVerifyIcs(unittest.TestCase):
    def _write(self, text):
        handle = tempfile.NamedTemporaryFile(
            suffix=".ics", delete=False, mode="wb")
        handle.write(text.encode("utf-8"))
        handle.close()
        return Path(handle.name)

    def test_minimal_valid_calendar_has_no_problems(self):
        text = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "BEGIN:VEVENT\r\n"
            "UID:a@b\r\n"
            "DTSTAMP:20260731T120000Z\r\n"
            "DTSTART;VALUE=DATE:20260812\r\n"
            "SUMMARY:Test\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        self.assertEqual(icsutil.verify_ics(self._write(text)), [])

    def test_missing_uid_is_reported(self):
        text = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "BEGIN:VEVENT\r\n"
            "DTSTAMP:20260731T120000Z\r\n"
            "DTSTART;VALUE=DATE:20260812\r\n"
            "SUMMARY:Test\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        problems = icsutil.verify_ics(self._write(text))
        self.assertTrue(any("UID" in p for p in problems))

    def test_bare_lf_is_reported(self):
        text = "BEGIN:VCALENDAR\nEND:VCALENDAR\n"
        problems = icsutil.verify_ics(self._write(text))
        self.assertTrue(any("LF" in p or "CRLF" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
