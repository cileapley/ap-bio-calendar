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
