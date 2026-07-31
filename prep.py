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
                    if target >= 0:
                        raw = ordered[target]
                        snapped = raw
                    else:
                        # The lead reaches back past the start of the year.
                        # Clamp the usable date to day one, but keep a real
                        # out-of-range raw_date so validate() can see it and
                        # fire its before-term warning. Silently clamping both
                        # makes a typo'd lead indistinguishable from a correct
                        # one that happens to land on day one.
                        raw = ordered[0] - timedelta(days=-target)
                        snapped = ordered[0]

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
                    # snapped_days means one thing everywhere: how many days
                    # earlier the usable date sits than the computed one,
                    # from an ordinary backward snap. The start-of-year clamp
                    # above is a different event — it pushes the date LATER,
                    # to the floor — so (raw - final) goes negative there.
                    # clamp to 0 rather than let that negative leak out:
                    # validate()/render_ics/render_html all read this field
                    # as "days moved back" and would render a negative as
                    # nonsense like "Moved back -7 days". The real signal for
                    # the overshoot case is that raw_date stays genuinely
                    # out of range; validate() keys its before-term warning
                    # on that instead.
                    snapped_days=max(0, (raw - final).days),
                ))

    actions.sort(key=lambda a: (a.date, ACTION_ORDER.index(a.action)))
    return actions
