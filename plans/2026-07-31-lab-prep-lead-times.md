# Lab Prep Lead Times Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive purchase-order, delivery and bench-prep dates from each investigation's scheduled lab day, and publish them as a teacher-facing page and subscribable feed.

**Architecture:** ICS text primitives are extracted from `build.py` into `icsutil.py` so both the student feed and the new prep feed can share them without a circular import. A new `prep.py` holds prep derivation, validation and the two prep renderers as pure functions. `build.py` keeps orchestration and the student outputs, and calls into `prep.py` after scheduling.

**Tech Stack:** Python 3.9+, PyYAML, `unittest` from the standard library. No new dependencies.

## Global Constraints

- **Dependencies:** Python 3 standard library + PyYAML only. Adding any other dependency requires asking first. Tests use `unittest`, NOT pytest.
- **No typed dates:** every published date must be derived. Nothing in `calendar.yaml` outside `non_instructional_days`, `site_testing_days` and `course:` may contain a literal date.
- **Student output isolation:** `docs/index.html`, `docs/calendar.ics` and `docs/calendar.json` must contain no prep data.
- **Self-contained HTML:** no network requests. No CDN, external fonts, remote images, or `url()` in CSS.
- **ICS conformance:** CRLF line endings, every physical line ≤ 75 octets, every VEVENT carries UID / DTSTAMP / DTSTART / SUMMARY.
- **Idempotent writes:** a rebuild that does not change the calendar must not rewrite any file. Timestamps alone do not count as a change.
- **Warn vs fail:** structural contradictions exit non-zero. Judgment calls print to stderr and exit zero.
- **Determinism:** `build.py` must not call `Date.now()`-equivalents inside pure functions. The build date is passed in as a parameter so tests can pin it.
- **Run tests with:** `python -m unittest discover -s tests -t . -v` from the repo root.

---

## File Structure

| File | Responsibility |
|---|---|
| `icsutil.py` | **Create.** iCalendar text primitives: escaping, line folding, slugs, and the structural validator. Knows nothing about calendars or labs. |
| `prep.py` | **Create.** Prep derivation, validation, and the two prep renderers. Pure functions; no file I/O. |
| `build.py` | **Modify.** Loses the ICS primitives to `icsutil.py`; gains prep wiring in `main()`. |
| `calendar.yaml` | **Modify.** Adds a `prep:` block to each of the eight lab entries. |
| `README.md` | **Modify.** Documents the prep feature and the two new URLs. |
| `tests/test_icsutil.py` | **Create.** Covers the extracted primitives. |
| `tests/test_prep.py` | **Create.** Covers derivation, validation and both renderers. |
| `tests/test_isolation.py` | **Create.** The leak test: prep never reaches student output. |

---

### Task 1: Extract ICS primitives into `icsutil.py`

Pure refactor. No behaviour change. This exists so `prep.py` can render an ICS feed without importing `build.py`, which would be circular.

**Files:**
- Create: `icsutil.py`
- Create: `tests/test_icsutil.py`
- Modify: `build.py` — delete `ics_escape` (line 393), `fold` (line 400), `slug` (line 419), `verify_ics` (line 486); add an import

**Interfaces:**
- Consumes: nothing
- Produces:
  - `icsutil.ics_escape(text: str) -> str`
  - `icsutil.fold(line: str) -> list[str]`
  - `icsutil.slug(*parts) -> str`
  - `icsutil.verify_ics(path: pathlib.Path) -> list[str]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_icsutil.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'icsutil'`

- [ ] **Step 3: Create `icsutil.py`**

Move the four functions out of `build.py` **verbatim** — do not rewrite them. `build.py` currently defines `ics_escape` at line 393, `fold` at line 400, `slug` at line 419 and `verify_ics` at line 486. Cut each one and paste it into this module header:

```python
#!/usr/bin/env python3
"""iCalendar text primitives.

Escaping, line folding, stable slugs, and a standard-library structural
validator. Knows nothing about calendars, labs or courses, so both the student
feed and the lab-prep feed can share it without a circular import.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
```

Then paste the four functions unchanged beneath it.

- [ ] **Step 4: Import them back into `build.py`**

Add near the other imports in `build.py`, after `import yaml`:

```python
from icsutil import fold, ics_escape, slug, verify_ics
```

`build.py` already imports `re`, `datetime` and `Path`, so leave those alone — `verify_ics` was the only user of `datetime.strptime` but `main()` still uses `datetime.now()`.

- [ ] **Step 5: Run the tests and the build**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 10 tests

Run: `python build.py`
Expected: `ICS validation          passed`, and `wrote  nothing — output already matches the source`

That second line is the proof the refactor changed nothing: byte-identical output.

- [ ] **Step 6: Commit**

```bash
git add icsutil.py tests/test_icsutil.py build.py
git commit -m "Extract ICS primitives into icsutil.py

Pure refactor ahead of the lab-prep feed, which needs the same escaping,
folding and validation. Importing them from build.py would be circular.

Output is byte-identical: the no-op rebuild writes nothing."
```

---

### Task 2: Prep date derivation

**Files:**
- Create: `prep.py`
- Create: `tests/test_prep.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `prep.BASIS: dict[str, str]` — `{"order": "calendar", "arrive": "calendar", "bench": "school"}`
  - `prep.ACTION_ORDER: tuple[str, ...]` — `("order", "arrive", "bench")`
  - `prep.PrepAction` — dataclass with fields `lab_id: str`, `lab_title: str`, `unit: int | None`, `action: str`, `lab_date: datetime.date`, `raw_date: datetime.date`, `date: datetime.date`, `lead_days: int`, `basis: str`, `snapped_days: int`
  - `prep.snap_back(day, instructional_days) -> datetime.date | None`
  - `prep.derive(blocks: list[dict], instructional_days: list[datetime.date]) -> list[PrepAction]`

`blocks` is the scheduled-block list produced by `build.schedule()`. Each entry dict already carries `id`, `title`, `kind` and `dates`. `derive` reads `prep` off the *source* entry, so `build.schedule()` must copy it through — that happens in Task 6.

- [ ] **Step 1: Write the failing test**

Create `tests/test_prep.py`:

```python
import unittest
from datetime import date, timedelta

import prep


def instructional(start, end, skip=()):
    """Weekdays from start to end inclusive, minus any dates in skip."""
    days, day = [], start
    while day <= end:
        if day.weekday() < 5 and day not in skip:
            days.append(day)
        day += timedelta(days=1)
    return days


def lab_block(lab_id, lab_date, prep_spec):
    return [{
        "unit": 3,
        "entries": [{
            "id": lab_id,
            "title": "Investigation X — Test Lab",
            "kind": "lab",
            "dates": [lab_date],
            "prep": prep_spec,
        }],
    }]


class TestSnapBack(unittest.TestCase):
    def setUp(self):
        self.days = set(instructional(date(2026, 8, 12), date(2026, 12, 18)))

    def test_instructional_day_snaps_to_itself(self):
        self.assertEqual(
            prep.snap_back(date(2026, 9, 15), self.days), date(2026, 9, 15))

    def test_saturday_snaps_back_to_friday(self):
        self.assertEqual(
            prep.snap_back(date(2026, 9, 19), self.days), date(2026, 9, 18))

    def test_date_before_the_first_day_returns_none(self):
        self.assertIsNone(prep.snap_back(date(2026, 8, 4), self.days))


class TestDeriveCalendarBasis(unittest.TestCase):
    def test_order_counts_calendar_days_then_snaps(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = lab_block("INV-4", date(2026, 9, 15), {"order": 21})
        actions = prep.derive(blocks, days)

        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.action, "order")
        self.assertEqual(action.basis, "calendar")
        self.assertEqual(action.raw_date, date(2026, 8, 25))
        self.assertEqual(action.date, date(2026, 8, 25))
        self.assertEqual(action.snapped_days, 0)

    def test_calendar_date_landing_on_a_weekend_snaps_backward(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        # Lab day Tue Sep 15 2026. A 2-day calendar lead lands on Sun Sep 13,
        # which must snap back to Fri Sep 11 — two days earlier, never later.
        blocks = lab_block("INV-4", date(2026, 9, 15), {"arrive": 2})
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].raw_date, date(2026, 9, 13))
        self.assertEqual(actions[0].date, date(2026, 9, 11))
        self.assertEqual(actions[0].snapped_days, 2)


class TestDeriveSchoolBasis(unittest.TestCase):
    def test_bench_counts_school_days_and_skips_the_weekend(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        # Tue Sep 15 minus 3 school days is Thu Sep 10.
        blocks = lab_block("INV-4", date(2026, 9, 15), {"bench": 3})
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].basis, "school")
        self.assertEqual(actions[0].date, date(2026, 9, 10))
        self.assertEqual(actions[0].snapped_days, 0)


class TestDeriveOverBreaks(unittest.TestCase):
    def test_arrival_inside_a_recess_snaps_out_of_it(self):
        recess = {date(2026, 12, 21) + timedelta(days=n) for n in range(12)}
        days = instructional(date(2026, 8, 12), date(2027, 2, 28), skip=recess)
        # Lab Jan 26; arrive 21 calendar days earlier is Jan 5 — but make the
        # lead long enough to land inside the recess.
        blocks = lab_block("INV-8", date(2027, 1, 26), {"arrive": 33})
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].raw_date, date(2026, 12, 24))
        self.assertEqual(actions[0].date, date(2026, 12, 18))
        self.assertEqual(actions[0].snapped_days, 6)


class TestDeriveShape(unittest.TestCase):
    def test_actions_come_back_in_chronological_order(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = lab_block(
            "INV-4", date(2026, 9, 15), {"order": 21, "arrive": 14, "bench": 2})
        actions = prep.derive(blocks, days)
        self.assertEqual([a.action for a in actions],
                         ["order", "arrive", "bench"])
        self.assertEqual(actions, sorted(actions, key=lambda a: a.date))

    def test_lab_without_a_prep_block_produces_nothing(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = [{"unit": 2, "entries": [{
            "id": "INV-4", "title": "T", "kind": "lab",
            "dates": [date(2026, 9, 15)]}]}]
        self.assertEqual(prep.derive(blocks, days), [])

    def test_non_lab_entries_are_ignored_even_with_a_prep_block(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = [{"unit": 2, "entries": [{
            "id": "2.7", "title": "Tonicity", "kind": "topic",
            "dates": [date(2026, 9, 15)], "prep": {"order": 21}}]}]
        self.assertEqual(prep.derive(blocks, days), [])

    def test_uses_the_labs_first_day_not_its_last(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = [{"unit": 2, "entries": [{
            "id": "INV-4", "title": "T", "kind": "lab",
            "dates": [date(2026, 9, 15), date(2026, 9, 16), date(2026, 9, 17)],
            "prep": {"bench": 1}}]}]
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].lab_date, date(2026, 9, 15))
        self.assertEqual(actions[0].date, date(2026, 9, 14))

    def test_unknown_action_key_raises(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = lab_block("INV-4", date(2026, 9, 15), {"deliver": 3})
        with self.assertRaises(ValueError):
            prep.derive(blocks, days)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prep'`

- [ ] **Step 3: Write `prep.py`**

```python
#!/usr/bin/env python3
"""Lab preparation lead times.

Derives purchase-order, delivery and bench-prep dates by subtracting lead times
from each investigation's first scheduled day, then renders them as a teacher
page and a subscribable feed.

Pure functions throughout: no file I/O, and the build date is always passed in
so tests can pin it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Each action counts its lead time on the basis that matches how it works.
# Purchasing and shipping run on calendar time and do not pause for holidays.
# Bench prep is work a person does at school, so it counts school days.
BASIS = {"order": "calendar", "arrive": "calendar", "bench": "school"}

# Intent order, earliest to latest. Used for tie-breaking on equal dates.
ACTION_ORDER = ("order", "arrive", "bench")

LABEL = {
    "order": "Order",
    "arrive": "Arrives",
    "bench": "Prep starts",
}


@dataclass(frozen=True)
class PrepAction:
    lab_id: str
    lab_title: str
    unit: int | None
    action: str
    lab_date: date
    raw_date: date
    date: date
    lead_days: int
    basis: str
    snapped_days: int


def snap_back(day: date, instructional_days) -> date | None:
    """Latest instructional day at or before `day`, or None if there is none.

    Backward only, by design: a computed deadline is never moved later.
    """
    available = {d for d in instructional_days if d <= day}
    return max(available) if available else None


def derive(blocks: list[dict], instructional_days: list[date]) -> list[PrepAction]:
    """Build every prep action implied by the scheduled blocks."""
    ordered = sorted(instructional_days)
    index = {day: i for i, day in enumerate(ordered)}
    actions: list[PrepAction] = []

    for block in blocks:
        for entry in block.get("entries", []):
            if entry.get("kind") != "lab":
                continue
            spec = entry.get("prep") or {}
            if not spec:
                continue
            dates = entry.get("dates") or []
            if not dates:
                continue
            lab_date = dates[0]

            for action, lead in spec.items():
                if action not in BASIS:
                    raise ValueError(
                        f"{entry.get('id')}: unknown prep action {action!r} — "
                        f"expected one of {sorted(BASIS)}"
                    )
                lead = int(lead)
                basis = BASIS[action]

                if basis == "calendar":
                    raw = lab_date - timedelta(days=lead)
                    snapped = snap_back(raw, ordered)
                else:
                    position = index.get(lab_date)
                    if position is None:
                        raise ValueError(
                            f"{entry.get('id')}: lab day {lab_date} is not an "
                            f"instructional day"
                        )
                    target = position - lead
                    raw = ordered[target] if target >= 0 else ordered[0]
                    snapped = raw if target >= 0 else None

                final = snapped if snapped is not None else raw
                actions.append(PrepAction(
                    lab_id=entry.get("id") or entry.get("title", ""),
                    lab_title=entry.get("title", ""),
                    unit=block.get("unit"),
                    action=action,
                    lab_date=lab_date,
                    raw_date=raw,
                    date=final,
                    lead_days=lead,
                    basis=basis,
                    snapped_days=(raw - final).days,
                ))

    actions.sort(key=lambda a: (a.date, ACTION_ORDER.index(a.action)))
    return actions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 22 tests

- [ ] **Step 5: Commit**

```bash
git add prep.py tests/test_prep.py
git commit -m "Derive lab prep dates from scheduled lab days

Three actions with fixed bases: order and arrive count calendar days because
purchasing and shipping run over breaks; bench counts school days because prep
is work done at school. Calendar-basis dates snap backward to an instructional
day, never forward, so a deadline is never moved later."
```

---

### Task 3: Prep validation and warnings

**Files:**
- Modify: `prep.py` — append `validate`
- Modify: `tests/test_prep.py` — append `TestValidate`

**Interfaces:**
- Consumes: `prep.PrepAction`, `prep.derive` from Task 2
- Produces: `prep.validate(actions, first_day: date, today: date) -> tuple[list[str], list[str]]` returning `(warnings, errors)`, each a list of human-readable strings

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prep.py`, above the `if __name__` block:

```python
class TestValidate(unittest.TestCase):
    def setUp(self):
        self.days = instructional(date(2026, 8, 12), date(2027, 2, 28))
        self.first = date(2026, 8, 12)

    def _actions(self, spec, lab_date=date(2026, 9, 15), lab_id="INV-4"):
        return prep.derive(lab_block(lab_id, lab_date, spec), self.days)

    def test_clean_actions_produce_nothing(self):
        actions = self._actions({"order": 21, "arrive": 14, "bench": 2})
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertEqual(warnings, [])
        self.assertEqual(errors, [])

    def test_date_in_the_past_warns(self):
        actions = self._actions({"order": 21})
        warnings, errors = prep.validate(actions, self.first, date(2026, 9, 1))
        self.assertEqual(errors, [])
        self.assertTrue(any("past" in w.lower() for w in warnings))

    def test_date_before_term_warns(self):
        # 42-day lead on a Sep 15 lab lands Aug 4, before the Aug 12 start.
        actions = self._actions({"order": 42})
        warnings, errors = prep.validate(actions, self.first, date(2026, 7, 1))
        self.assertEqual(errors, [])
        self.assertTrue(any("before" in w.lower() for w in warnings))

    def test_snapping_more_than_two_days_warns(self):
        recess = {date(2026, 12, 21) + timedelta(days=n) for n in range(12)}
        days = instructional(date(2026, 8, 12), date(2027, 2, 28), skip=recess)
        actions = prep.derive(
            lab_block("INV-8", date(2027, 1, 26), {"arrive": 33}), days)
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertEqual(errors, [])
        self.assertTrue(any("break" in w.lower() for w in warnings))

    def test_snapping_two_days_or_less_does_not_warn(self):
        # A weekend snap of 1-2 days is routine, not worth a warning.
        actions = self._actions({"arrive": 2})
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertEqual(errors, [])
        self.assertFalse(any("break" in w.lower() for w in warnings))

    def test_arrive_before_order_is_an_error(self):
        actions = self._actions({"order": 7, "arrive": 21})
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertTrue(any("INV-4" in e for e in errors))

    def test_errors_name_the_lab(self):
        actions = self._actions({"order": 7, "arrive": 21}, lab_id="INV-9")
        _, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertTrue(any("INV-9" in e for e in errors))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `AttributeError: module 'prep' has no attribute 'validate'`

- [ ] **Step 3: Append `validate` to `prep.py`**

```python
# A snap of a day or two is a routine weekend adjustment. More than that means
# the date crossed a recess and the effective deadline moved meaningfully.
SNAP_WARNING_THRESHOLD = 2


def validate(actions, first_day: date, today: date):
    """Split prep problems into warnings and hard errors.

    Warnings are facts about the world — a window that has closed, or one that
    falls in the summer. Errors are contradictions in the source file.
    """
    warnings: list[str] = []
    errors: list[str] = []

    for action in actions:
        where = f"{action.lab_id} {action.action}"
        if action.date < today:
            warnings.append(
                f"{where}: {action.date} is in the past "
                f"({(today - action.date).days} days ago)"
            )
        if action.raw_date < first_day:
            warnings.append(
                f"{where}: {action.raw_date} falls before the first day of "
                f"school — this belongs to the summer"
            )
        if action.snapped_days > SNAP_WARNING_THRESHOLD:
            warnings.append(
                f"{where}: {action.raw_date} lands in a break and snapped back "
                f"{action.snapped_days} days to {action.date}"
            )

    by_lab: dict[str, dict[str, PrepAction]] = {}
    for action in actions:
        by_lab.setdefault(action.lab_id, {})[action.action] = action
    for lab_id, found in by_lab.items():
        order, arrive = found.get("order"), found.get("arrive")
        if order and arrive and arrive.date < order.date:
            errors.append(
                f"{lab_id}: arrive ({arrive.date}) is before order "
                f"({order.date}) — the lead times contradict each other"
            )

    return warnings, errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 29 tests

- [ ] **Step 5: Commit**

```bash
git add prep.py tests/test_prep.py
git commit -m "Validate prep dates: warn on facts, fail on contradictions

Past dates and summer dates are facts about the world and only warn — failing
on them would make the build unusable for the rest of the year. A snap of more
than two days means a recess was crossed and the real deadline moved. Only
arrive-before-order is a contradiction in the source, so only that errors."
```

---

### Task 4: Prep ICS renderer

**Files:**
- Modify: `prep.py` — append `render_ics`
- Modify: `tests/test_prep.py` — append `TestRenderIcs`

**Interfaces:**
- Consumes: `prep.PrepAction`, `icsutil.fold`, `icsutil.ics_escape`, `icsutil.slug`
- Produces: `prep.render_ics(actions, course: dict, stamp_utc: str, uid_domain: str) -> str`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prep.py`:

```python
class TestRenderIcs(unittest.TestCase):
    def setUp(self):
        self.days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        self.course = {"title": "AP Biology", "school_year": "2026-27"}
        self.actions = prep.derive(
            lab_block("INV-4", date(2026, 9, 15),
                      {"order": 21, "arrive": 14, "bench": 2}),
            self.days)

    def _render(self):
        return prep.render_ics(
            self.actions, self.course, "20260731T120000Z", "apbio-2026-27")

    def test_uses_crlf_line_endings(self):
        text = self._render()
        self.assertIn("\r\n", text)
        # No bare LF: every newline must be preceded by a carriage return.
        for position, char in enumerate(text):
            if char == "\n":
                self.assertEqual(text[position - 1], "\r")

    def test_one_vevent_per_action(self):
        self.assertEqual(self._render().count("BEGIN:VEVENT"), 3)

    def test_summary_names_the_action_and_the_lab_date(self):
        text = self._render()
        self.assertIn("SUMMARY:Order: Investigation X — Test Lab", text)
        self.assertIn("lab Sep 15", text)

    def test_uids_are_stable_and_distinct(self):
        first = self._render()
        second = prep.render_ics(
            self.actions, self.course, "20260801T090000Z", "apbio-2026-27")
        uids = lambda t: sorted(
            l for l in t.split("\r\n") if l.startswith("UID:"))
        self.assertEqual(uids(first), uids(second))
        self.assertEqual(len(set(uids(first))), 3)

    def test_uid_does_not_contain_the_date(self):
        # UIDs keyed on the date would duplicate events when a unit slips.
        for line in self._render().split("\r\n"):
            if line.startswith("UID:"):
                self.assertNotIn("2026", line)

    def test_all_day_events_end_the_following_day(self):
        text = self._render()
        self.assertIn("DTSTART;VALUE=DATE:20260825", text)
        self.assertIn("DTEND;VALUE=DATE:20260826", text)

    def test_calendar_name_marks_it_as_the_prep_feed(self):
        self.assertIn("X-WR-CALNAME:AP Biology 2026-27 Lab Prep",
                      self._render())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `AttributeError: module 'prep' has no attribute 'render_ics'`

- [ ] **Step 3: Append `render_ics` to `prep.py`**

Add to the imports at the top of `prep.py`:

```python
from icsutil import fold, ics_escape, slug
```

Then append:

```python
def _short(day: date) -> str:
    return f"{day.strftime('%b')} {day.day}"


def render_ics(actions, course: dict, stamp_utc: str, uid_domain: str) -> str:
    """One all-day VEVENT per prep action.

    UIDs are keyed on lab and action, never on the date, so a slipped unit
    moves the event in a subscriber's calendar instead of duplicating it.
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{course['title']} {course['school_year']}//lab prep//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(course['title'])} "
        f"{ics_escape(course['school_year'])} Lab Prep",
        "X-PUBLISHED-TTL:PT12H",
    ]

    for action in actions:
        summary = (f"{LABEL[action.action]}: {action.lab_title} "
                   f"(lab {_short(action.lab_date)})")
        description = (
            f"{action.lead_days} {action.basis} days before "
            f"{action.lab_date.isoformat()}."
        )
        if action.snapped_days:
            description += (
                f" Moved back {action.snapped_days} day(s) from "
                f"{action.raw_date.isoformat()} to land on a school day."
            )
        event = [
            "BEGIN:VEVENT",
            f"UID:prep-{slug(action.lab_id, action.action)}@{uid_domain}",
            f"DTSTAMP:{stamp_utc}",
            f"DTSTART;VALUE=DATE:{action.date.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:"
            f"{(action.date + timedelta(days=1)).strftime('%Y%m%d')}",
            "TRANSP:TRANSPARENT",
            f"SUMMARY:{ics_escape(summary)}",
            f"DESCRIPTION:{ics_escape(description)}",
            "END:VEVENT",
        ]
        for line in event:
            lines.extend(fold(line))

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 36 tests

- [ ] **Step 5: Commit**

```bash
git add prep.py tests/test_prep.py
git commit -m "Render the lab prep ICS feed

UIDs key on lab and action rather than date, so when a unit slips the event
moves in a subscriber's calendar instead of duplicating."
```

---

### Task 5: Prep HTML renderer

**Files:**
- Modify: `prep.py` — append `render_html`
- Modify: `tests/test_prep.py` — append `TestRenderHtml`

**Interfaces:**
- Consumes: `prep.PrepAction`
- Produces: `prep.render_html(actions, course: dict, stamp: str, today: date) -> str`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prep.py`:

```python
class TestRenderHtml(unittest.TestCase):
    def setUp(self):
        self.days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        self.course = {"title": "AP Biology", "school_year": "2026-27"}
        self.actions = prep.derive(
            lab_block("INV-4", date(2026, 9, 15),
                      {"order": 21, "arrive": 14, "bench": 2}),
            self.days)

    def _render(self, today=date(2026, 8, 1)):
        return prep.render_html(self.actions, self.course,
                                "2026-07-31 12:00", today)

    def test_declares_charset_and_viewport(self):
        html = self._render()
        self.assertIn('<meta charset="utf-8">', html)
        self.assertIn('name="viewport"', html)

    def test_makes_no_network_requests(self):
        import re as _re
        html = self._render()
        self.assertEqual(_re.findall(r'(?:src|href)\s*=', html), [])
        self.assertNotIn("@import", html)
        self.assertNotIn("url(", html)

    def test_lists_every_action(self):
        html = self._render()
        for label in ("Order", "Arrives", "Prep starts"):
            self.assertIn(label, html)

    def test_groups_by_month(self):
        self.assertIn("August 2026", self._render())

    def test_marks_past_actions(self):
        html = self._render(today=date(2026, 9, 20))
        self.assertIn("overdue", html.lower())

    def test_escapes_html_in_titles(self):
        actions = prep.derive(
            [{"unit": 2, "entries": [{
                "id": "INV-X", "title": "Lab <script>alert(1)</script>",
                "kind": "lab", "dates": [date(2026, 9, 15)],
                "prep": {"bench": 1}}]}],
            self.days)
        html = prep.render_html(actions, self.course, "s", date(2026, 8, 1))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty_action_list_still_renders_a_page(self):
        html = prep.render_html([], self.course, "s", date(2026, 8, 1))
        self.assertIn("<title>", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `AttributeError: module 'prep' has no attribute 'render_html'`

- [ ] **Step 3: Append `render_html` to `prep.py`**

Add `import html as _html` to the imports at the top of `prep.py`, then append:

```python
PREP_CSS = """
*,*::before,*::after{box-sizing:border-box}
body{margin:0;padding:1.25rem;font:16px/1.55 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#1c2024;background:#fff}
.wrap{max-width:52rem;margin:0 auto}
h1{margin:0 0 .15rem;font-size:1.5rem;letter-spacing:-.01em}
.sub{margin:0 0 1.25rem;color:#5b6470;font-size:.9rem}
h2{margin:1.5rem 0 .5rem;font-size:1rem;color:#3d4650;
border-bottom:1px solid #e4e8ec;padding-bottom:.3rem}
.row{display:grid;grid-template-columns:5.5rem 6.5rem 1fr;gap:.15rem .8rem;
padding:.5rem .2rem;border-bottom:1px solid #f1f4f7;align-items:baseline}
.row.overdue{background:#fdf0f3}
.when{color:#5b6470;font-size:.85rem;font-variant-numeric:tabular-nums}
.tag{display:inline-block;padding:.1rem .45rem;border-radius:999px;
font-size:.7rem;font-weight:600;text-transform:uppercase;white-space:nowrap}
.tag.order{background:#eaf1f8;color:#1c5d99}
.tag.arrive{background:#e6f4ec;color:#1d6b42}
.tag.bench{background:#fdefe6;color:#a2521a}
.what .note{display:block;color:#5b6470;font-size:.8rem;margin-top:.1rem}
.flag{color:#a03050;font-weight:600}
footer{margin-top:2rem;padding-top:.8rem;border-top:1px solid #eef1f4;
color:#8a939e;font-size:.75rem}
@media (max-width:640px){
body{padding:.85rem}
.row{grid-template-columns:1fr;gap:.1rem}
}
"""


def render_html(actions, course: dict, stamp: str, today: date) -> str:
    """Teacher-facing prep schedule. Self-contained, no network requests."""
    def esc(value):
        return _html.escape(str(value), quote=True)

    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(course['title'])} Lab Prep "
        f"{esc(course['school_year'])}</title>",
        f"<style>{PREP_CSS}</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        f"<h1>Lab Prep Schedule</h1>",
        f'<p class="sub">{esc(course["title"])} '
        f'{esc(course["school_year"])} &middot; {len(actions)} actions</p>',
    ]

    current_month = None
    for action in actions:
        month = action.date.strftime("%B %Y")
        if month != current_month:
            parts.append(f"<h2>{esc(month)}</h2>")
            current_month = month

        overdue = " overdue" if action.date < today else ""
        note = esc(f"{action.lead_days} {action.basis} days before "
                   f"{_short(action.lab_date)}")
        if action.snapped_days:
            # Integer interpolation only — no caller-supplied text in this span.
            note += (' &middot; <span class="flag">moved back '
                     f'{int(action.snapped_days)} day(s) out of a break</span>')

        parts.append(
            f'<div class="row{overdue}">'
            f'<div class="when">{esc(_short(action.date))}</div>'
            f'<div><span class="tag {esc(action.action)}">'
            f'{esc(LABEL[action.action])}</span></div>'
            f'<div class="what">{esc(action.lab_title)}'
            f'<span class="note">{note}</span></div>'
            "</div>"
        )

    parts.append(
        f'<footer>Generated {esc(stamp)} from calendar.yaml. '
        f'Teacher-facing — not linked from the student calendar.</footer>')
    parts.append("</div></body></html>")
    return "\n".join(parts) + "\n"
```

Note: every caller-supplied value goes through `esc`. The one raw-markup branch interpolates `int(action.snapped_days)` and nothing else, so no untrusted text reaches the page unescaped.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 43 tests

- [ ] **Step 5: Commit**

```bash
git add prep.py tests/test_prep.py
git commit -m "Render the lab prep HTML page

Chronological, grouped by month, overdue rows flagged. Self-contained with
inline CSS and no network requests, same constraint as the student page."
```

---

### Task 6: Wire prep into the build

The integration task. Its deliverable is real `docs/prep.html` and `docs/prep.ics` generated from `calendar.yaml`, so it carries the calendar data and the documentation.

**Files:**
- Modify: `build.py` — `schedule()` (carry `prep` through), `main()` (derive, validate, write, report)
- Modify: `calendar.yaml` — add `prep:` to the eight lab entries
- Modify: `README.md` — document the feature and the two URLs
- Create: `tests/test_isolation.py`

**Interfaces:**
- Consumes: `prep.derive`, `prep.validate`, `prep.render_ics`, `prep.render_html` from Tasks 2–5; `build.write_if_changed`, `build.UID_DOMAIN`, `build.DIST`
- Produces: `docs/prep.html`, `docs/prep.ics`

- [ ] **Step 1: Write the failing isolation test**

Create `tests/test_isolation.py`:

```python
"""Prep data must never reach student-facing output."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

STUDENT_FILES = ["index.html", "calendar.ics", "calendar.json"]
PREP_MARKERS = ["Prep starts", "Arrives", "prep-inv", "Lab Prep",
                "Order: Investigation"]


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
        sys.path.insert(0, str(ROOT))
        import icsutil
        self.assertEqual(icsutil.verify_ics(DOCS / "prep.ics"), [])

    def test_rebuild_is_idempotent(self):
        before = {n: (DOCS / n).read_bytes()
                  for n in STUDENT_FILES + ["prep.html", "prep.ics"]}
        subprocess.run([sys.executable, "build.py"], cwd=ROOT,
                       capture_output=True, text=True)
        for name, content in before.items():
            self.assertEqual((DOCS / name).read_bytes(), content,
                             f"docs/{name} was rewritten with no change")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_isolation -v`
Expected: FAIL — `docs/prep.html` does not exist

- [ ] **Step 3: Carry `prep` through the scheduler**

In `build.py`, inside `schedule()`, the `out_entries.append({...})` block (around line 285) lists the fields copied from each source entry. Add one line after `"link": entry.get("link"),`:

```python
                "prep": entry.get("prep"),
```

- [ ] **Step 4: Add the eight prep blocks to `calendar.yaml`**

Replace each lab line with the version below. Defaults are from general lab practice, **not vendor data** — override once real PO cycles are known.

```yaml
      - {id: "INV-4", title: "Investigation 4 — Diffusion and Osmosis", kind: lab, notes: "Big Idea 2: Energetics.", prep: {order: 21, arrive: 14, bench: 2}}
      - {id: "INV-13", title: "Investigation 13 — Enzyme Activity", kind: lab, notes: "Big Idea 4: System Interactions.", prep: {order: 21, arrive: 7, bench: 2}}
      - {id: "INV-5", title: "Investigation 5 — Photosynthesis", kind: lab, notes: "Big Idea 2: Energetics.", prep: {order: 21, arrive: 3, bench: 1}}
      - {id: "INV-6", title: "Investigation 6 — Cellular Respiration", kind: lab, notes: "Big Idea 2: Energetics.", prep: {order: 21, arrive: 14, bench: 5}}
      - {id: "INV-7", title: "Investigation 7 — Cell Division: Mitosis and Meiosis", kind: lab, notes: "Big Idea 3: Information Storage and Transmission.", prep: {order: 21, arrive: 14, bench: 5}}
      - {id: "INV-8", title: "Investigation 8 — Biotechnology: Bacterial Transformation", kind: lab, notes: "Big Idea 3: Information Storage and Transmission.", prep: {order: 28, arrive: 7, bench: 3}}
      - {id: "INV-2", title: "Investigation 2 — Mathematical Modeling: Hardy–Weinberg", kind: lab, notes: "Big Idea 1: Evolution.", prep: {order: 14, bench: 1}}
      - {id: "INV-3", title: "Investigation 3 — Comparing DNA Sequences with BLAST", kind: lab, notes: "Big Idea 1: Evolution. Computer-based, no consumables.", prep: {bench: 1}}
```

Add this comment block immediately above the `blocks:` key, after the existing SEQUENCE documentation:

```yaml
#   prep:        lead times for a lab, in days. Three keys, each with a fixed
#                basis chosen to match how that step actually works:
#                  order   calendar days — purchasing runs over breaks
#                  arrive  calendar days — shipping runs on calendar time
#                  bench   school days   — prep is work done at school
#                Calendar-basis dates snap BACKWARD to an instructional day, so
#                a deadline is never moved later. Any key may be omitted.
#                These values are defaults from general lab practice, NOT vendor
#                data. Replace them with your real PO cycle and kit lead times.
```

- [ ] **Step 5: Wire prep into `main()`**

In `build.py`, add to the imports after `from icsutil import ...`:

```python
import prep as prep_module
```

In `main()`, immediately after the `blocks = publishable(sched)` line inside the `try` block, add:

```python
        try:
            prep_actions = prep_module.derive(sched["blocks"], all_days)
        except ValueError as exc:
            # derive() raises ValueError on a malformed prep block. main()
            # only catches BuildError, so translate it or it escapes as a
            # traceback instead of the clean failure message.
            raise BuildError(f"Bad prep block in calendar.yaml: {exc}") from exc

        prep_warnings, prep_errors = prep_module.validate(
            prep_actions, all_days[0], date.today())
        if prep_errors:
            raise BuildError(
                "Lab prep lead times contradict each other:\n  - "
                + "\n  - ".join(prep_errors)
                + "\n\nFix the prep block in calendar.yaml."
            )
```

Then, alongside the existing three `write_if_changed` calls, add two more entries to the `written` dict:

```python
        "prep.ics": write_if_changed(
            DIST / "prep.ics",
            prep_module.render_ics(
                prep_actions, course, stamp_utc, UID_DOMAIN)),
        "prep.html": write_if_changed(
            DIST / "prep.html",
            prep_module.render_html(
                prep_actions, course, stamp_local, date.today())),
```

**Do not change `VOLATILE`.** Its existing patterns already cover both new files: `prep.ics` carries `DTSTAMP:` lines, and `prep.html`'s footer matches the `Generated \d{4}-\d\d-\d\d \d\d:\d\d from calendar\.yaml` pattern because `render_html` receives `stamp_local`, which uses that exact format. Confirm by running the build twice and checking the second run reports writing nothing.

After the `review before exam` print line, add:

```python
    print(f"  lab prep                {len(prep_actions)} actions across "
          f"{len({a.lab_id for a in prep_actions})} labs"
          + (f" — {len(prep_warnings)} need attention" if prep_warnings else ""))
    for warning in prep_warnings:
        print(f"    ! {warning}", file=sys.stderr)
```

Finally, extend the ICS validation to cover the prep feed. Replace the single `problems = verify_ics(DIST / "calendar.ics")` line with:

```python
    problems = (verify_ics(DIST / "calendar.ics")
                + [f"prep.ics: {p}" for p in verify_ics(DIST / "prep.ics")])
```

- [ ] **Step 6: Run the build and inspect**

Run: `python build.py`
Expected: a `lab prep  21 actions across 8 labs` line, `ICS validation passed`, and `wrote  docs/prep.ics, docs/prep.html`

Run: `python build.py` again
Expected: `wrote  nothing — output already matches the source`

- [ ] **Step 7: Run the full test suite**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 48 tests

- [ ] **Step 8: Document in `README.md`**

Add this section immediately after the `## The lab program` section:

```markdown
## Lab prep lead times

Each investigation declares how far ahead its purchase order, delivery and
bench prep have to happen. Those dates are **derived from the lab's scheduled
day**, so when a unit slips they slip with it.

```yaml
prep: {order: 21, arrive: 7, bench: 3}
```

| Key | Meaning | Counted in |
|---|---|---|
| `order` | Submit the purchase order by this date | calendar days — purchasing runs over breaks |
| `arrive` | Materials must be in the building | calendar days — shipping runs on calendar time |
| `bench` | Start hands-on prep | school days — prep happens at school |

Calendar-basis dates snap **backward** to an instructional day, never forward,
so a deadline is never moved later. When a snap crosses a recess by more than
two days the build says so — that is the case where naive arithmetic gives a
deadline later than the real one.

**The lead times shipped here are defaults from general lab practice, not
vendor data.** Replace them with your district's real PO cycle and your
supplier's kit lead times. Each is one number on one line.

### Where it goes

| | |
|---|---|
| Prep schedule | `https://cileapley.github.io/ap-bio-calendar/prep.html` |
| Prep feed | `https://cileapley.github.io/ap-bio-calendar/prep.ics` |

Subscribe to `prep.ics` yourself; students subscribe to `calendar.ics`. Prep
never appears in the student page, feed or JSON — there is a test for that.

Both prep files are publicly reachable, because the repo is public and that is
what makes Pages free. Nothing in them is sensitive — "order spinach" is not a
secret — but a student could find them. Known property, not a surprise.
```

Also update the `## Publishing` URL table to list both new files, and the
`## What the build reports` sample output to include the `lab prep` line.

- [ ] **Step 9: Run the full suite and build one final time**

Run: `python -m unittest discover -s tests -t . -v && python build.py`
Expected: 48 tests PASS; build reports `nothing — output already matches the source`

- [ ] **Step 10: Commit and push**

```bash
git add build.py calendar.yaml README.md tests/test_isolation.py docs/
git commit -m "Publish lab prep lead times

Derives order, arrival and bench-prep dates for all eight investigations from
their scheduled lab days, and publishes docs/prep.html and docs/prep.ics.

Prep never reaches the student page, feed or JSON; tests/test_isolation.py
enforces that and checks the rebuild stays idempotent.

Lead times are defaults from general lab practice, not vendor data."
git push origin main
```

---

## Verification against the spec

Run through this after Task 6.

| Spec requirement | Where |
|---|---|
| Three keys with fixed bases | Task 2, `prep.BASIS` |
| Snap backward to instructional day | Task 2, `prep.snap_back` |
| Derive from lab's **first** day | Task 2, `test_uses_the_labs_first_day_not_its_last` |
| Past-date warning | Task 3, `test_date_in_the_past_warns` |
| Before-term warning | Task 3, `test_date_before_term_warns` |
| Break-crossing warning (>2 days) | Task 3, `test_snapping_more_than_two_days_warns` |
| `arrive` before `order` fails the build | Task 3, `test_arrive_before_order_is_an_error`; Task 6, `BuildError` |
| `docs/prep.ics` with stable UIDs | Task 4, `test_uids_are_stable_and_distinct` |
| `docs/prep.html`, self-contained | Task 5, `test_makes_no_network_requests` |
| Student output isolation | Task 6, `tests/test_isolation.py` |
| ICS structural validation on prep feed | Task 6, `test_prep_ics_is_structurally_valid` |
| Idempotent rebuild | Task 6, `test_rebuild_is_idempotent` |
| Summary line | Task 6, Step 5 |
| Defaults marked as non-authoritative | Task 6, Steps 4 and 8 |

**Cascade test** — spec test 4, run manually once after Task 6:

```bash
# Shift the year by a week and confirm prep dates move with it.
python - <<'EOF'
from pathlib import Path
p = Path("calendar.yaml"); orig = p.read_text(encoding="utf-8")
p.write_text(orig.replace("first_instructional_day: 2026-08-12",
                          "first_instructional_day: 2026-08-19"), encoding="utf-8")
EOF
python build.py            # prep dates should all move later
git diff --stat docs/
git checkout -- calendar.yaml && python build.py
git status --short docs/   # must be empty: byte-identical after revert
```
