# Calendar Change Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report what changed in the course calendar between the last committed build and the working tree, for the teacher in prose and for the lesson-plan workspace as JSON.

**Architecture:** A new `changes.py` split the way `prep.py` and `build.py` already split — a pure `diff(old, new)` over two parsed calendars with no I/O, plus a thin CLI that fetches the baseline from git and renders both outputs. Nothing in `build.py` changes; it keeps its git-free property.

**Tech Stack:** Python 3.9+, standard library only. `unittest`. No PyYAML — this tool reads JSON, not the source file.

## Global Constraints

- **Dependencies:** Python 3 standard library only for `changes.py`. Tests use `unittest`, NOT pytest. Do not add any dependency.
- **Run tests with:** `python -m unittest discover -s tests -t . -v` from the repo root. `tests/__init__.py` already exists — leave it.
- **Purity:** `diff()` performs no I/O, calls no git, and reads no clock. Every test builds dicts by hand.
- **Never a gate:** a changed calendar is never an error. Exit 0 for any set of changes including none. Exit 1 only when an input cannot be read or parsed.
- **`build.py` is not modified by this plan.** It has no git dependency today and must keep none.
- **`changes.json` is gitignored** and written to the repository root, never to `docs/`.
- **`lost_day_indices` carries raw integers**, never formatted keys like `INV-4-d3`. The `{id}-d{n}` format is this project's suggestion to the lesson-plan workspace, not their published contract.

---

## File Structure

| File | Responsibility |
|---|---|
| `changes.py` | **Create.** `EntryDelta`, `diff()`, the two renderers, and a `main()` CLI. ~150 lines. |
| `tests/test_changes.py` | **Create.** Sixteen cases against pure `diff()`, plus eight renderer and three CLI checks. |
| `.gitignore` | **Modify.** Add `changes.json`. |
| `README.md` | **Modify.** Document the command. |

One new module. `diff()` and the renderers are small and change together, so they stay in one file rather than splitting a 150-line tool across three.

---

### Task 1: The diff engine

**Files:**
- Create: `changes.py`
- Create: `tests/test_changes.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `changes.EntryDelta` — frozen dataclass, fields `entry_id: str`, `kind: str`, `title: str`, `changes: tuple[str, ...]`, `old: dict | None`, `new: dict | None`, `lost_day_indices: tuple[int, ...]`
  - `changes.SEVERITY: tuple[str, ...]` — `("REMOVED", "RESIZED", "MOVED", "ADDED", "RETITLED")`
  - `changes.entry_key(block: dict, entry: dict) -> str`
  - `changes.diff(old: dict, new: dict) -> list[EntryDelta]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_changes.py`:

```python
import unittest

import changes


def calendar(*entries):
    """A minimal calendar.json shaped document containing one block.

    Each argument is a dict overriding the defaults below, so a test only
    states the fields it cares about.
    """
    built = []
    for e in entries:
        entry = {"id": None, "title": "T", "kind": "topic", "skill": None,
                 "notes": None, "link": None, "periods": 1,
                 "start": "2026-09-15", "end": "2026-09-15",
                 "dates": ["2026-09-15"]}
        entry.update(e)
        built.append(entry)
    return {"blocks": [{"id": "unit-2", "unit": 2, "title": "Cells",
                        "entries": built}]}


class TestNoChange(unittest.TestCase):
    def test_identical_calendars_produce_nothing(self):
        cal = calendar({"id": "2.7", "periods": 3})
        self.assertEqual(changes.diff(cal, cal), [])

    def test_unrelated_fields_are_ignored(self):
        # `skill` and `notes` are not part of the join contract.
        old = calendar({"id": "2.7", "skill": "4.A"})
        new = calendar({"id": "2.7", "skill": "9.Z", "notes": "hi"})
        self.assertEqual(changes.diff(old, new), [])


class TestResize(unittest.TestCase):
    def test_shrinking_reports_the_lost_indices(self):
        old = calendar({"id": "INV-4", "kind": "lab", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "kind": "lab", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-16"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.entry_id, "INV-4")
        self.assertIn("RESIZED", delta.changes)
        self.assertEqual(delta.lost_day_indices, (3,))

    def test_shrinking_by_two_reports_both_indices(self):
        old = calendar({"id": "INV-4", "periods": 3, "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "periods": 1, "end": "2026-09-15"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.lost_day_indices, (2, 3))

    def test_growing_loses_no_days(self):
        old = calendar({"id": "INV-4", "periods": 2, "end": "2026-09-16"})
        new = calendar({"id": "INV-4", "periods": 3, "end": "2026-09-17"})
        (delta,) = changes.diff(old, new)
        self.assertIn("RESIZED", delta.changes)
        self.assertEqual(delta.lost_day_indices, ())

    def test_a_pure_resize_is_not_also_reported_as_a_move(self):
        # Shrinking moves the end date as a direct consequence. Reporting that
        # as a move too would flag every resized entry twice.
        old = calendar({"id": "INV-4", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-16"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("RESIZED",))


class TestMove(unittest.TestCase):
    def test_changed_start_is_a_move(self):
        old = calendar({"id": "2.7", "start": "2026-09-15", "end": "2026-09-15"})
        new = calendar({"id": "2.7", "start": "2026-09-16", "end": "2026-09-16"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("MOVED",))

    def test_same_length_sliding_end_is_a_move(self):
        # A holiday inserted mid-entry keeps the length but pushes the end.
        old = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-16"})
        new = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-17"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("MOVED",))

    def test_an_entry_can_move_and_resize_in_one_delta(self):
        old = calendar({"id": "2.7", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-21", "end": "2026-09-22"})
        deltas = changes.diff(old, new)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(set(deltas[0].changes), {"MOVED", "RESIZED"})


class TestAddRemove(unittest.TestCase):
    def test_new_id_is_added(self):
        (delta,) = changes.diff(calendar(), calendar({"id": "2.7"}))
        self.assertEqual(delta.changes, ("ADDED",))
        self.assertIsNone(delta.old)
        self.assertIsNotNone(delta.new)

    def test_vanished_id_is_removed(self):
        (delta,) = changes.diff(calendar({"id": "2.7"}), calendar())
        self.assertEqual(delta.changes, ("REMOVED",))
        self.assertIsNone(delta.new)
        self.assertIsNotNone(delta.old)

    def test_removed_entry_keeps_its_old_title(self):
        old = calendar({"id": "2.7", "title": "Tonicity"})
        (delta,) = changes.diff(old, calendar())
        self.assertEqual(delta.title, "Tonicity")


class TestRetitle(unittest.TestCase):
    def test_changed_title_is_reported(self):
        old = calendar({"id": "2.7", "title": "Tonicity"})
        new = calendar({"id": "2.7", "title": "Tonicity and Osmoregulation"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("RETITLED",))
        self.assertEqual(delta.title, "Tonicity and Osmoregulation")


class TestIdlessEntries(unittest.TestCase):
    def test_idless_entry_matches_on_block_and_title(self):
        # Four real entries carry no id: the opening block and the two `fill`
        # review blocks. Matching them by position would report the whole year
        # as changed the moment an entry is inserted above them.
        cal = calendar({"id": None, "title": "Post-exam project"})
        self.assertEqual(changes.diff(cal, cal), [])

    def test_idless_entry_still_reports_a_move(self):
        old = calendar({"id": None, "title": "Post-exam project",
                        "start": "2027-05-04"})
        new = calendar({"id": None, "title": "Post-exam project",
                        "start": "2027-05-05"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.entry_id, "unit-2:Post-exam project")
        self.assertEqual(delta.changes, ("MOVED",))


class TestOrdering(unittest.TestCase):
    def test_deltas_come_back_most_consequential_first(self):
        old = calendar({"id": "gone"}, {"id": "shrink", "periods": 3,
                                        "end": "2026-09-17"},
                       {"id": "slide", "start": "2026-09-15"},
                       {"id": "rename", "title": "Old"})
        new = calendar({"id": "shrink", "periods": 2, "end": "2026-09-16"},
                       {"id": "slide", "start": "2026-09-20",
                        "end": "2026-09-20"},
                       {"id": "rename", "title": "New"},
                       {"id": "fresh"})
        order = [d.changes[0] for d in changes.diff(old, new)]
        self.assertEqual(order, ["REMOVED", "RESIZED", "MOVED",
                                 "ADDED", "RETITLED"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'changes'`

- [ ] **Step 3: Write `changes.py`**

```python
#!/usr/bin/env python3
"""What changed in the course calendar since the last committed build.

Two audiences. The teacher needs prose — "Unit 4 Assessment moved to Dec 2" —
to tell a class. The lesson-plan workspace needs to know which entry ids and
day indices stopped existing, because its plans are keyed to them.

`diff()` is pure: two parsed calendars in, deltas out. No I/O, no git, no clock.
"""

from __future__ import annotations

from dataclasses import dataclass

# Most consequential first. A removal loses written work; a retitle is cosmetic.
SEVERITY = ("REMOVED", "RESIZED", "MOVED", "ADDED", "RETITLED")

# The fields that constitute the join contract. Everything else in an entry —
# skill codes, notes, links — can change without affecting a lesson plan's key.
TRACKED = ("periods", "start", "end", "title")


@dataclass(frozen=True)
class EntryDelta:
    entry_id: str
    kind: str
    title: str
    changes: tuple[str, ...]
    old: dict | None
    new: dict | None
    lost_day_indices: tuple[int, ...]


def entry_key(block: dict, entry: dict) -> str:
    """Stable identity for an entry across two builds.

    Ids are unique where present. Four entries have none — the course opening
    and the two `fill` review blocks — and those fall back to block plus title.
    Position is deliberately not used: inserting one entry would renumber
    everything after it and report the whole year as changed.
    """
    if entry.get("id"):
        return str(entry["id"])
    return f"{block.get('id')}:{entry.get('title', '')}"


def _index(calendar: dict) -> dict[str, tuple[dict, dict]]:
    out: dict[str, tuple[dict, dict]] = {}
    for block in calendar.get("blocks", []):
        for entry in block.get("entries", []):
            out[entry_key(block, entry)] = (block, entry)
    return out


def _tracked(entry: dict) -> dict:
    return {field: entry.get(field) for field in TRACKED}


def diff(old: dict, new: dict) -> list[EntryDelta]:
    """Entry-level changes between two parsed calendar.json documents."""
    old_index, new_index = _index(old), _index(new)
    deltas: list[EntryDelta] = []

    for key in sorted(set(old_index) | set(new_index)):
        old_pair, new_pair = old_index.get(key), new_index.get(key)

        if new_pair is None:
            _, entry = old_pair
            deltas.append(EntryDelta(
                key, entry.get("kind", ""), entry.get("title", ""),
                ("REMOVED",), _tracked(entry), None, ()))
            continue

        if old_pair is None:
            _, entry = new_pair
            deltas.append(EntryDelta(
                key, entry.get("kind", ""), entry.get("title", ""),
                ("ADDED",), None, _tracked(entry), ()))
            continue

        before, after = _tracked(old_pair[1]), _tracked(new_pair[1])
        if before == after:
            continue

        found: list[str] = []
        resized = before["periods"] != after["periods"]
        if resized:
            found.append("RESIZED")
        # Not "start or end differs": shrinking an entry moves its end date as
        # a direct consequence, and reporting that as a move as well would flag
        # every resized entry twice. Requiring periods to hold isolates the
        # case that is genuinely a move — an entry that kept its length but
        # slid, which is what an inserted holiday does.
        if before["start"] != after["start"] or (
                not resized and before["end"] != after["end"]):
            found.append("MOVED")
        if before["title"] != after["title"]:
            found.append("RETITLED")

        lost: tuple[int, ...] = ()
        if resized:
            old_periods = int(before["periods"] or 0)
            new_periods = int(after["periods"] or 0)
            if new_periods < old_periods:
                lost = tuple(range(new_periods + 1, old_periods + 1))

        deltas.append(EntryDelta(
            key, new_pair[1].get("kind", ""), after["title"],
            tuple(sorted(found, key=SEVERITY.index)),
            before, after, lost))

    deltas.sort(key=lambda d: (SEVERITY.index(d.changes[0]), d.entry_id))
    return deltas
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 81 tests (65 existing + 16 new)

- [ ] **Step 5: Commit**

```bash
git add changes.py tests/test_changes.py
git commit -m "Diff two parsed calendars into entry-level deltas

A pure function: two calendar.json documents in, deltas out. No I/O, no git,
no clock, so tests build dicts by hand.

MOVED deliberately requires periods to be unchanged. Shrinking an entry moves
its end date as a direct consequence, and treating that as a move as well would
flag every resized entry twice."
```

---

### Task 2: The two renderers

**Files:**
- Modify: `changes.py` — append `render_text` and `render_json`
- Modify: `tests/test_changes.py` — append `TestRenderText` and `TestRenderJson`

**Interfaces:**
- Consumes: `changes.EntryDelta`, `changes.diff`, `changes.SEVERITY` from Task 1
- Produces:
  - `changes.render_text(deltas: list[EntryDelta]) -> str`
  - `changes.render_json(deltas: list[EntryDelta]) -> str`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_changes.py`, above the `if __name__` block:

```python
class TestRenderText(unittest.TestCase):
    def _deltas(self):
        old = calendar({"id": "INV-4", "kind": "lab",
                        "title": "Investigation 4", "periods": 3,
                        "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "kind": "lab",
                        "title": "Investigation 4", "periods": 2,
                        "end": "2026-09-16"})
        return changes.diff(old, new)

    def test_empty_input_says_nothing_changed(self):
        text = changes.render_text([])
        self.assertIn("No changes", text)

    def test_groups_under_a_severity_heading(self):
        self.assertIn("RESIZED", changes.render_text(self._deltas()))

    def test_shows_the_period_transition(self):
        self.assertIn("3 days -> 2", changes.render_text(self._deltas()))

    def test_names_the_orphaned_key_as_a_hint(self):
        # The JSON stays convention-free; the human summary spells the key out
        # because "orphans INV-4-d3" is what tells you which file to delete.
        self.assertIn("INV-4-d3", changes.render_text(self._deltas()))

    def test_reports_what_did_not_change(self):
        text = changes.render_text(self._deltas())
        self.assertIn("Nothing", text)


class TestRenderJson(unittest.TestCase):
    def _deltas(self):
        old = calendar({"id": "INV-4", "periods": 3, "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "periods": 2, "end": "2026-09-16"})
        return changes.diff(old, new)

    def test_output_is_valid_json_with_a_stable_shape(self):
        import json
        payload = json.loads(changes.render_json(self._deltas()))
        self.assertIn("changes", payload)
        self.assertIn("counts", payload)
        self.assertEqual(payload["counts"]["RESIZED"], 1)

    def test_lost_days_are_raw_integers_not_formatted_keys(self):
        # The {id}-d{n} format is this project's suggestion to the lesson-plan
        # workspace, not their published contract. Baking a guess at another
        # project's key format into this output would make the two disagree
        # silently the moment they diverge.
        import json
        payload = json.loads(changes.render_json(self._deltas()))
        entry = payload["changes"][0]
        self.assertEqual(entry["lost_day_indices"], [3])
        self.assertNotIn("INV-4-d3", changes.render_json(self._deltas()))

    def test_empty_input_still_produces_a_valid_document(self):
        import json
        payload = json.loads(changes.render_json([]))
        self.assertEqual(payload["changes"], [])
        self.assertEqual(payload["counts"], {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `AttributeError: module 'changes' has no attribute 'render_text'`

- [ ] **Step 3: Append the renderers to `changes.py`**

Add `import json` to the imports at the top of `changes.py`, then append:

```python
def render_text(deltas: list[EntryDelta]) -> str:
    """Prose for the teacher, grouped most consequential first."""
    if not deltas:
        return "No changes to the calendar since the last commit.\n"

    lines = ["Calendar changes vs HEAD", ""]
    seen: set[str] = set()

    for heading in SEVERITY:
        group = [d for d in deltas if heading in d.changes]
        if not group:
            continue
        seen.add(heading)
        lines.append(f"{heading}  {len(group)} "
                     f"{'entry' if len(group) == 1 else 'entries'}")
        for delta in group:
            detail = ""
            if heading == "RESIZED":
                detail = (f"{delta.old['periods']} days -> "
                          f"{delta.new['periods']}")
                if delta.lost_day_indices:
                    keys = ", ".join(f"{delta.entry_id}-d{n}"
                                     for n in delta.lost_day_indices)
                    detail += f"   orphans {keys}"
            elif heading == "MOVED":
                detail = (f"{delta.old['start']}..{delta.old['end']} -> "
                          f"{delta.new['start']}..{delta.new['end']}")
            elif heading == "RETITLED":
                detail = f"{delta.old['title']!r} -> {delta.new['title']!r}"
            elif heading == "ADDED":
                detail = f"{delta.new['start']}, {delta.new['periods']} day(s)"
            elif heading == "REMOVED":
                detail = f"was {delta.old['start']}, {delta.old['periods']} day(s)"
            lines.append(f"  {delta.entry_id:<12} {delta.title[:44]:<46}{detail}")
        lines.append("")

    quiet = [h for h in SEVERITY if h not in seen]
    if quiet:
        lines.append("Nothing " + ", ".join(h.lower() for h in quiet) + ".")
    return "\n".join(lines) + "\n"


def render_json(deltas: list[EntryDelta]) -> str:
    """Machine-readable, for consumers keyed to entry ids and day indices."""
    counts: dict[str, int] = {}
    for delta in deltas:
        for name in delta.changes:
            counts[name] = counts.get(name, 0) + 1

    payload = {
        "counts": counts,
        "changes": [
            {
                "entry_id": d.entry_id,
                "kind": d.kind,
                "title": d.title,
                "changes": list(d.changes),
                "old": d.old,
                "new": d.new,
                "lost_day_indices": list(d.lost_day_indices),
            }
            for d in deltas
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 89 tests

- [ ] **Step 5: Commit**

```bash
git add changes.py tests/test_changes.py
git commit -m "Render calendar deltas for both audiences

Prose groups by severity and spells out orphaned lesson-plan keys, because
'orphans INV-4-d3' is what tells you which file to delete. The JSON stays
convention-free and emits raw day indices instead."
```

---

### Task 3: The CLI

The integration task. Its deliverable is a working `python changes.py`, so it carries the gitignore entry and the documentation.

**Files:**
- Modify: `changes.py` — append `git_baseline`, `load_current`, `main`
- Modify: `tests/test_changes.py` — append `TestBaseline`
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Consumes: `changes.diff`, `changes.render_text`, `changes.render_json` from Tasks 1–2
- Produces: `python changes.py` writing `changes.json` and printing to stdout

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_changes.py`:

```python
class TestBaseline(unittest.TestCase):
    def test_missing_baseline_is_not_an_error(self):
        # Before the first commit there is nothing to compare against. That is
        # a fact about the repository, not a failure.
        text, code = changes.report(None, {"blocks": []})
        self.assertEqual(code, 0)
        self.assertIn("No git baseline", text)

    def test_present_baseline_produces_a_report(self):
        old = calendar({"id": "2.7", "periods": 2, "end": "2026-09-16"})
        new = calendar({"id": "2.7", "periods": 1, "end": "2026-09-15"})
        text, code = changes.report(old, new)
        self.assertEqual(code, 0)
        self.assertIn("RESIZED", text)

    def test_identical_calendars_exit_zero(self):
        cal = calendar({"id": "2.7"})
        text, code = changes.report(cal, cal)
        self.assertEqual(code, 0)
        self.assertIn("No changes", text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL with `AttributeError: module 'changes' has no attribute 'report'`

- [ ] **Step 3: Append the CLI to `changes.py`**

Add these imports to the top of `changes.py`: `import subprocess` and `from pathlib import Path`. Do not add `sys` — `raise SystemExit` needs no import and an unused one is exactly what a reviewer flags. Then append:

```python
ROOT = Path(__file__).resolve().parent
CURRENT = ROOT / "docs" / "calendar.json"
MACHINE = ROOT / "changes.json"   # gitignored: see the note in main()


def git_baseline() -> dict | None:
    """The last committed calendar, or None when there is nothing to compare.

    Absence is normal — a fresh clone before the first build, or a repository
    where docs/calendar.json has never been committed. Both report cleanly
    rather than failing.
    """
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:docs/calendar.json"],
            cwd=ROOT, capture_output=True, text=True)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        # A non-zero git exit means "not committed yet", which is normal and
        # returns None above. Reaching here means git produced a file that is
        # not valid JSON — a corrupt committed calendar, which is a real
        # problem and must not be silently reported as "no baseline".
        raise SystemExit(
            f"HEAD:docs/calendar.json is not valid JSON: {exc}")


def load_current() -> dict:
    if not CURRENT.exists():
        raise SystemExit(
            f"{CURRENT.relative_to(ROOT)} not found. Run `python build.py` first.")
    try:
        return json.loads(CURRENT.read_bytes().decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{CURRENT.relative_to(ROOT)} is not valid JSON: {exc}")


def report(old: dict | None, new: dict) -> tuple[str, int]:
    """Render the comparison. Never returns a non-zero code for a change."""
    if old is None:
        return ("No git baseline to compare against — nothing committed yet.\n",
                0)
    return render_text(diff(old, new)), 0


def main() -> int:
    current = load_current()
    baseline = git_baseline()
    text, code = report(baseline, current)
    print(text, end="")

    if baseline is not None:
        # Written to the repository root and gitignored, deliberately. In docs/
        # and committed, the next build's diff against HEAD would be empty,
        # which would change this file again — a loop that leaves the tree
        # permanently dirty. docs/ is also what Pages publishes; this is
        # working state, not published output.
        MACHINE.write_bytes(
            render_json(diff(baseline, current)).encode("utf-8"))
        print(f"\nMachine-readable: {MACHINE.name}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 92 tests

- [ ] **Step 5: Add the gitignore entry**

Append to `.gitignore`:

```
# Working state from changes.py, never committed: see the note in its main()
changes.json
```

- [ ] **Step 6: Verify against real data**

Run: `python changes.py`
Expected: `No changes to the calendar since the last commit.` — the working tree matches HEAD.

Then prove it detects the motivating case. Run these one at a time:

```bash
python -c "import pathlib; p=pathlib.Path('calendar.yaml'); b=p.read_bytes(); p.write_bytes(b.replace(b'default_lab_periods: 2', b'default_lab_periods: 3'))"
python build.py
python changes.py
```

Expected: a `RESIZED` group naming eight investigations, each `2 days -> 3`, with no orphaned keys (growth loses nothing), plus `MOVED` entries for the spring units that shifted.

Then restore and confirm the report goes quiet:

```bash
git checkout -- calendar.yaml
python build.py
python changes.py
```

Expected: `No changes to the calendar since the last commit.`

Confirm `git status --short` shows only `changes.json` as untracked, or nothing if the gitignore entry landed.

- [ ] **Step 7: Document it in `README.md`**

Add this section immediately after the `## Publishing` section:

```markdown
## What changed?

```
python changes.py
```

Compares the working tree's `docs/calendar.json` against the last committed
one and reports what moved. Run it after a rebuild and before committing.

Prose goes to stdout, grouped most-consequential-first — removed, resized,
moved, added, retitled:

```
RESIZED  8 entries
  INV-4    Investigation 4 — Diffusion and Osmosis   3 days -> 2   orphans INV-4-d3
```

`changes.json` holds the same thing machine-readably, for the lesson-plan
workspace, which keys its plans to entry ids and day indices. It is gitignored:
committing it would make the next diff empty, changing the file again.

The report is never a gate. A changed calendar is not an error — the only
non-zero exit is a missing or unparseable `docs/calendar.json`.
```

- [ ] **Step 8: Run the full suite and commit**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 92 tests

```bash
git add changes.py tests/test_changes.py .gitignore README.md
git commit -m "Add the changes.py CLI

Baseline comes from git show HEAD:docs/calendar.json. A missing baseline is
normal, not an error — a fresh clone has nothing to compare against.

changes.json is gitignored and lives at the root rather than in docs/:
committing it would make the next diff empty, which would change the file
again, and docs/ is published output rather than working state."
git push origin main
```

---

## Verification against the spec

| Spec requirement | Where |
|---|---|
| `diff(old, new)` pure, no I/O | Task 1 |
| `EntryDelta` shape | Task 1, Step 3 |
| Match on id, fall back to `block_id:title` | Task 1, `entry_key`; `TestIdlessEntries` |
| One delta per entry carrying all change types | Task 1, `test_an_entry_can_move_and_resize_in_one_delta` |
| `lost_day_indices` raw, never formatted | Task 2, `test_lost_days_are_raw_integers_not_formatted_keys` |
| Growth loses no days | Task 1, `test_growing_loses_no_days` |
| MOVED excludes resize-implied end changes | Task 1, `test_a_pure_resize_is_not_also_reported_as_a_move` |
| Five change types | Tasks 1–2 |
| Severity ordering | Task 1, `TestOrdering` |
| Prose to stdout, JSON to gitignored root file | Task 3 |
| Missing baseline exits 0 | Task 3, `test_missing_baseline_is_not_an_error` |
| Missing/unparseable current exits 1 | Task 3, `load_current` |
| Never a gate | Task 3, `report` always returns 0 |
| Real-data check on the lab change | Task 3, Step 6 |
| `build.py` unmodified | No task touches it |
