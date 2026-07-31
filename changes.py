#!/usr/bin/env python3
"""What changed in the course calendar since the last committed build.

Two audiences. The teacher needs prose — "Unit 4 Assessment moved to Dec 2" —
to tell a class. The lesson-plan workspace needs to know which entry ids and
day indices stopped existing, because its plans are keyed to them.

`diff()` is pure: two parsed calendars in, deltas out. No I/O, no git, no clock.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

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


def render_text(deltas: list[EntryDelta]) -> str:
    """Prose for the teacher, grouped most consequential first."""
    if not deltas:
        return "No changes to the calendar since the last commit.\n"

    lines = [f"Calendar changes vs HEAD — {len(deltas)} "
             f"{'entry' if len(deltas) == 1 else 'entries'} changed", ""]
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
            cwd=ROOT, capture_output=True)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    try:
        # Decode explicitly rather than passing text=True: that decodes with
        # the locale codepage (cp1252 on Windows) while git emits UTF-8, which
        # silently mangles every em dash and middle dot in the calendar.
        return json.loads(result.stdout.decode("utf-8"))
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
