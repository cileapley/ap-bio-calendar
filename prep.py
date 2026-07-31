#!/usr/bin/env python3
"""Lab preparation lead times.

Derives purchase-order, delivery and bench-prep dates by subtracting lead times
from each investigation's first scheduled day, then renders them as a teacher
page and a subscribable feed.

Pure functions throughout: no file I/O, and the build date is always passed in
so tests can pin it.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass
from datetime import date, timedelta

from icsutil import fold, ics_escape, slug

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


def _short(day: date) -> str:
    return f"{day.strftime('%b')} {day.day}"


def render_ics(actions, course: dict, stamp_utc: str, uid_domain: str) -> str:
    """One all-day VEVENT per prep action.

    UIDs are keyed on lab and action, never on the date, so a slipped unit
    moves the event in a subscriber's calendar instead of duplicating it.
    """
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{course['title']} {course['school_year']}//lab prep//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(course['title'])} "
        f"{ics_escape(course['school_year'])} Lab Prep",
        "X-PUBLISHED-TTL:PT12H",
    ]
    lines: list[str] = []
    for line in header:
        lines.extend(fold(line))

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
