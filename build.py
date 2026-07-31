#!/usr/bin/env python3
"""
Build the AP Biology 2026-27 student-facing calendar from calendar.yaml.

    python build.py

Reads  : calendar.yaml
Writes : docs/index.html    self-contained student page (embed as an iframe)
         docs/calendar.ics  subscribable all-day feed
         docs/calendar.json structured data

`docs/` is what GitHub Pages serves. Rebuild, commit, push, and the class site
sees the change — there is no separate deploy step.

Nothing here hardcodes a date. Every published date is resolved by walking the
sequence in calendar.yaml across the real instructional days, so editing the
source file and rebuilding cascades correctly.

Requires: Python 3.9+, PyYAML. Nothing else.
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required.  pip install pyyaml")

from icsutil import fold, ics_escape, slug, verify_ics

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "calendar.yaml"
DIST = ROOT / "docs"          # GitHub Pages serves this folder from main

WEEKDAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
UID_DOMAIN = "apbio-2026-27"


class BuildError(Exception):
    """Fatal problem with the calendar source. Reported, never papered over."""


# Substrings that change on every build without the calendar changing. They are
# blanked before comparing old output to new, so a rebuild that produces the
# same calendar leaves the files — and therefore `git status` — untouched.
VOLATILE = [
    re.compile(r"DTSTAMP:\d{8}T\d{6}Z"),
    re.compile(r'"generated":\s*"[^"]*"'),
    re.compile(r"Generated \d{4}-\d\d-\d\d \d\d:\d\d from calendar\.yaml"),
]


def write_if_changed(path: Path, content: str) -> bool:
    """Write only when the substantive content differs. Returns True if written.

    Everything is written as UTF-8 bytes with no newline translation, so the
    .ics keeps the CRLF endings RFC 5545 requires and the rest stay LF.
    """
    def normalise(text: str) -> str:
        for pattern in VOLATILE:
            text = pattern.sub("<volatile>", text)
        return text

    if path.exists():
        try:
            existing = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            existing = None
        if existing is not None and normalise(existing) == normalise(content):
            return False
    path.write_bytes(content.encode("utf-8"))
    return True


# ---------------------------------------------------------------------------
# Load and normalise
# ---------------------------------------------------------------------------

def load_source() -> dict:
    if not SOURCE.exists():
        raise BuildError(f"{SOURCE.name} not found next to build.py")
    with SOURCE.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    for key in ("course", "assumptions", "blocks"):
        if key not in data:
            raise BuildError(f"calendar.yaml is missing the '{key}' section")
    return data


def as_date(value, label: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise BuildError(f"{label} is not a date: {value!r}")


def expand_exceptions(entries, label: str) -> dict[date, str]:
    """Flatten single dates and inclusive ranges into {date: reason}."""
    out: dict[date, str] = {}
    for item in entries or []:
        reason = item.get("reason", label)
        if "date" in item:
            out[as_date(item["date"], label)] = reason
        elif "from" in item and "to" in item:
            start = as_date(item["from"], label)
            end = as_date(item["to"], label)
            if end < start:
                raise BuildError(f"{label}: range ends before it starts ({start} to {end})")
            day = start
            while day <= end:
                out[day] = reason
                day += timedelta(days=1)
        else:
            raise BuildError(f"{label}: entry needs either 'date' or 'from'+'to' — got {item!r}")
    return out


# ---------------------------------------------------------------------------
# Instructional day index
# ---------------------------------------------------------------------------

def build_day_index(course: dict, closed: dict[date, str], testing: dict[date, str]):
    """Every day the section actually meets, in order. This is the spine."""
    first = as_date(course["first_instructional_day"], "first_instructional_day")
    last = as_date(course["last_instructional_day"], "last_instructional_day")
    if last < first:
        raise BuildError("last_instructional_day falls before first_instructional_day")

    if course.get("meets_daily", True):
        meets = {WEEKDAYS[d] for d in ("Mon", "Tue", "Wed", "Thu", "Fri")}
    else:
        names = course.get("meets_on") or []
        if not names:
            raise BuildError("meets_daily is false but meets_on is empty")
        unknown = [n for n in names if n not in WEEKDAYS]
        if unknown:
            raise BuildError(f"meets_on has unknown weekday(s): {unknown}")
        meets = {WEEKDAYS[n] for n in names}

    days: list[date] = []
    day = first
    while day <= last:
        if day.weekday() in meets and day not in closed and day not in testing:
            days.append(day)
        day += timedelta(days=1)
    if not days:
        raise BuildError("No instructional days found — check the course dates and holidays")
    return days


# ---------------------------------------------------------------------------
# Schedule the sequence across the day index
# ---------------------------------------------------------------------------

def contiguous_runs(days: list[date]) -> list[tuple[date, date]]:
    """Group consecutive calendar days so a break splits an entry cleanly."""
    runs: list[tuple[date, date]] = []
    for day in days:
        if runs and day - runs[-1][1] == timedelta(days=1):
            runs[-1] = (runs[-1][0], day)
        else:
            runs.append((day, day))
    return runs


def build_pools(course: dict, all_days: list[date], exam_day: date):
    """Split the year into the four phases the sequence draws from.

    fall   — through the last content day of semester 1
    finals — the semester 1 final exam block, off limits to content
    spring — from the start of semester 2 up to the day before the AP exam
    post   — after the AP exam

    The exam day itself belongs to no phase; it is a fixed anchor.
    """
    brk = course.get("semester_break") or {}
    last_fall = brk.get("last_content_day")
    finals_len = int(brk.get("finals_days", 0))

    if not last_fall:
        return {"fall": [d for d in all_days if d < exam_day],
                "finals": [], "spring": [],
                "post": [d for d in all_days if d > exam_day]}

    last_fall = as_date(last_fall, "semester_break.last_content_day")
    fall = [d for d in all_days if d <= last_fall]
    rest = [d for d in all_days if last_fall < d < exam_day]
    finals = rest[:finals_len]
    spring = rest[finals_len:]
    if len(finals) < finals_len:
        raise BuildError(
            f"Only {len(finals)} instructional day(s) available after "
            f"{last_fall} for a {finals_len}-day finals block"
        )
    return {"fall": fall, "finals": finals, "spring": spring,
            "post": [d for d in all_days if d > exam_day]}


def schedule(data: dict, all_days: list[date], pools_src: dict):
    course = data["course"]
    assumptions = data["assumptions"]
    exam_day = as_date(course["exam_date"], "exam_date")

    lab_periods = int(assumptions.get("default_lab_periods", 2))
    labs_additive = bool(assumptions.get("labs_additive", True))

    pools = {k: list(v) for k, v in pools_src.items()}

    scheduled_blocks = []
    overflow: list[str] = []
    unscheduled_labs = 0

    for block in data["blocks"]:
        pool_key = block.get("phase", "fall")
        if pool_key not in pools:
            raise BuildError(
                f"block '{block.get('id')}' has unknown phase {pool_key!r} — "
                f"expected one of {sorted(pools)}"
            )
        out_entries = []

        for entry in block.get("entries", []):
            kind = entry.get("kind", "topic")
            label = entry.get("title", entry.get("id", "(untitled)"))

            # How many days does this entry want?
            if kind == "lab" and "periods" not in entry:
                want = lab_periods if labs_additive else 0
            else:
                want = entry.get("periods", 1)

            if want == "fill":
                take = len(pools[pool_key])
            elif kind == "lab" and not labs_additive:
                take = 0
            else:
                try:
                    take = int(want)
                except (TypeError, ValueError):
                    raise BuildError(f"'{label}': periods must be a number or 'fill', got {want!r}")
                if take < 0:
                    raise BuildError(f"'{label}': periods cannot be negative")

            if kind == "lab" and not labs_additive:
                unscheduled_labs += 1

            available = len(pools[pool_key])
            if take > available:
                overflow.append(
                    f"[{pool_key}] {label} — wanted {take} period(s), {available} left"
                )
                take = available

            days = pools[pool_key][:take]
            del pools[pool_key][:take]

            out_entries.append({
                "id": entry.get("id"),
                "title": entry.get("title", ""),
                "kind": kind,
                "skill": entry.get("skill"),
                "notes": entry.get("notes"),
                "link": entry.get("link"),
                "visibility": entry.get("visibility", "student"),
                "periods": take,
                "dates": days,
                "start": days[0] if days else None,
                "end": days[-1] if days else None,
                "runs": contiguous_runs(days),
            })

        dated = [e for e in out_entries if e["dates"]]
        scheduled_blocks.append({
            "id": block.get("id"),
            "unit": block.get("unit"),
            "title": block.get("title", ""),
            "weight": block.get("weight"),
            "ced_periods_45": block.get("ced_periods_45"),
            "planned": block.get("planned"),
            "phase": pool_key,
            "after_exam": pool_key == "post",
            "entries": out_entries,
            "start": dated[0]["start"] if dated else None,
            "end": dated[-1]["end"] if dated else None,
            "periods": sum(e["periods"] for e in out_entries),
        })

    if overflow:
        raise BuildError(
            "The sequence does not fit. Ran out of instructional days at:\n  - "
            + "\n  - ".join(overflow)
            + "\n\nThat phase is full. Free a day inside it — drop a flex day, "
              "trim a topic, or remove an investigation — then rebuild. Days "
              "cannot be borrowed across the semester boundary or the AP exam."
        )

    # A phase with days left over means content stops early and the calendar
    # has a hole. Only phases ending in a `fill` block should end empty.
    leftovers = {k: len(v) for k, v in pools.items() if v}

    return {
        "blocks": scheduled_blocks,
        "exam_day": exam_day,
        "pre_days": pools_src["fall"] + pools_src["finals"] + pools_src["spring"],
        "post_days": pools_src["post"],
        "leftovers": leftovers,
        "unscheduled_labs": unscheduled_labs,
    }


# ---------------------------------------------------------------------------
# Publishable view — teacher-only entries stripped here, once, for all outputs
# ---------------------------------------------------------------------------

def publishable(sched: dict) -> list[dict]:
    out = []
    for block in sched["blocks"]:
        entries = [e for e in block["entries"]
                   if e["visibility"] != "teacher" and e["dates"]]
        if not entries:
            continue
        pub = dict(block)
        pub["entries"] = entries
        pub["start"] = entries[0]["start"]
        pub["end"] = entries[-1]["end"]
        out.append(pub)
    return out


# ---------------------------------------------------------------------------
# Output — JSON
# ---------------------------------------------------------------------------

def iso(value):
    return value.isoformat() if value else None


def render_json(data: dict, sched: dict, blocks: list[dict], summary: dict, stamp: str) -> str:
    payload = {
        "generated": stamp,
        "source": "calendar.yaml",
        "course": {
            "title": data["course"]["title"],
            "school_year": data["course"]["school_year"],
            "exam_date": iso(sched["exam_day"]),
            "exam_note": data["course"].get("exam_note"),
            "period_minutes": data["course"].get("period_minutes"),
        },
        "summary": summary,
        "blocks": [
            {
                "id": b["id"],
                "unit": b["unit"],
                "title": b["title"],
                "weight": b["weight"],
                "start": iso(b["start"]),
                "end": iso(b["end"]),
                "periods": sum(e["periods"] for e in b["entries"]),
                "entries": [
                    {
                        "id": e["id"],
                        "title": e["title"],
                        "kind": e["kind"],
                        "skill": e["skill"],
                        "notes": e["notes"],
                        "link": e["link"],
                        "periods": e["periods"],
                        "start": iso(e["start"]),
                        "end": iso(e["end"]),
                        "dates": [iso(d) for d in e["dates"]],
                    }
                    for e in b["entries"]
                ],
            }
            for b in blocks
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Output — iCalendar
# ---------------------------------------------------------------------------

def render_ics(data: dict, sched: dict, blocks: list[dict], stamp_utc: str) -> str:
    course = data["course"]
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{course['title']} {course['school_year']}//calendar.yaml//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(course['title'])} {ics_escape(course['school_year'])}",
        "X-PUBLISHED-TTL:PT12H",
    ]
    lines: list[str] = []
    for line in header:
        lines.extend(fold(line))

    def event(uid: str, start: date, end_inclusive: date, summary: str, description: str, url=None):
        block = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp_utc}",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(end_inclusive + timedelta(days=1)).strftime('%Y%m%d')}",
            "TRANSP:TRANSPARENT",
            f"SUMMARY:{ics_escape(summary)}",
        ]
        if description:
            block.append(f"DESCRIPTION:{ics_escape(description)}")
        if url:
            block.append(f"URL:{ics_escape(url)}")
        block.append("END:VEVENT")
        for entry in block:
            lines.extend(fold(entry))

    # The exam is a fixed anchor from course config, not part of any block.
    event(
        f"exam@{UID_DOMAIN}",
        sched["exam_day"], sched["exam_day"],
        f"AP Biology Exam — {course.get('exam_note', '')}".strip(" —"),
        f"{course['title']} AP Exam.",
    )

    for block in blocks:
        prefix = f"Unit {block['unit']} — " if block["unit"] else ""
        for entry in block["entries"]:
            bits = []
            if entry["id"]:
                bits.append(entry["id"])
            bits.append(block["title"])
            if entry["skill"]:
                bits.append(f"Science practice {entry['skill']}")
            if entry["notes"]:
                bits.append(entry["notes"])
            description = " · ".join(bits)

            for index, (start, end) in enumerate(entry["runs"]):
                uid = f"{slug(block['id'], entry['id'] or entry['title'])}-{index}@{UID_DOMAIN}"
                label = f"{prefix}{entry['title']}"
                if len(entry["runs"]) > 1:
                    label += f" (part {index + 1} of {len(entry['runs'])})"
                event(uid, start, end, label, description, entry["link"])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------------------
# Output — student-facing HTML
# ---------------------------------------------------------------------------

CSS = """
*,*::before,*::after{box-sizing:border-box}
body{margin:0;padding:1.25rem;font:16px/1.55 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#1c2024;background:#fff}
.wrap{max-width:60rem;margin:0 auto}
h1{margin:0 0 .15rem;font-size:1.5rem;letter-spacing:-.01em}
.sub{margin:0 0 1rem;color:#5b6470;font-size:.9rem}
.exam{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:baseline;
padding:.7rem .9rem;margin-bottom:1rem;border:1px solid #d8dde3;border-left:4px solid #1c5d99;
border-radius:6px;background:#f6f9fc}
.exam strong{font-size:1.05rem}
.exam span{color:#5b6470;font-size:.85rem}
.legend{display:flex;flex-wrap:wrap;gap:.4rem .8rem;margin-bottom:1.25rem;
font-size:.78rem;color:#5b6470}
.tag{display:inline-block;padding:.1rem .45rem;border-radius:999px;font-size:.7rem;
font-weight:600;letter-spacing:.02em;text-transform:uppercase;white-space:nowrap}
.tag.topic{background:#eaf1f8;color:#1c5d99}
.tag.lab{background:#e6f4ec;color:#1d6b42}
.tag.assessment{background:#fdefe6;color:#a2521a}
.tag.review{background:#f0ecf9;color:#5a3fa0}
.tag.flex{background:#fdf0f3;color:#a03050}
.tag.opening{background:#eef0f2;color:#4a5560}
details{border:1px solid #dfe4ea;border-radius:8px;margin-bottom:.6rem;overflow:hidden}
details[open]{border-color:#c8d1da}
summary{cursor:pointer;padding:.7rem .9rem;background:#fafbfc;font-weight:600;
display:flex;flex-wrap:wrap;gap:.15rem .7rem;align-items:baseline;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"\\25B8";display:inline-block;color:#8a939e;font-weight:400;
transition:transform .15s ease}
details[open] summary::before{transform:rotate(90deg)}
summary .meta{margin-left:auto;font-weight:400;color:#5b6470;font-size:.82rem}
.rows{border-top:1px solid #eef1f4}
.row{display:grid;grid-template-columns:9.5rem 1fr;gap:.15rem .9rem;
padding:.55rem .9rem;border-bottom:1px solid #f1f4f7}
.row:last-child{border-bottom:none}
.row.now{background:#fffbe8;box-shadow:inset 3px 0 0 #d9a300}
.when{color:#5b6470;font-size:.82rem;font-variant-numeric:tabular-nums;padding-top:.1rem}
.what{min-width:0}
.what .id{font-weight:600;color:#3d4650;margin-right:.3rem}
.what .note{display:block;color:#5b6470;font-size:.82rem;margin-top:.15rem}
.what a{color:#1c5d99}
.now-badge{display:none;margin-left:.4rem;padding:.05rem .4rem;border-radius:999px;
background:#d9a300;color:#fff;font-size:.65rem;font-weight:700;text-transform:uppercase}
.row.now .now-badge{display:inline-block}
footer{margin-top:1.5rem;padding-top:.8rem;border-top:1px solid #eef1f4;
color:#8a939e;font-size:.75rem}
@media (max-width:640px){
body{padding:.85rem}
.row{grid-template-columns:1fr;gap:.1rem}
.when{font-size:.78rem}
summary .meta{margin-left:0;width:100%}
}
"""

JS = """
(function(){
  var now=new Date();
  var day=now.getDay();
  var monday=new Date(now.getFullYear(),now.getMonth(),now.getDate()-((day+6)%7));
  var friday=new Date(monday.getFullYear(),monday.getMonth(),monday.getDate()+4);
  function parse(s){var p=s.split("-");return new Date(+p[0],+p[1]-1,+p[2]);}
  var first=null;
  document.querySelectorAll(".row").forEach(function(row){
    var start=parse(row.dataset.start),end=parse(row.dataset.end);
    if(end>=monday&&start<=friday){row.classList.add("now");if(!first)first=row;}
  });
  if(first){
    var box=first.closest("details");
    if(box){box.open=true;}
    document.querySelectorAll("details").forEach(function(d){
      if(d!==box)d.open=false;
    });
  }
})();
"""

LONG = "%A, %B %-d" if sys.platform != "win32" else "%A, %B %#d"
SHORT = "%b %-d" if sys.platform != "win32" else "%b %#d"


def date_range_label(start: date, end: date) -> str:
    if start == end:
        return start.strftime(f"{SHORT}").replace(" 0", " ")
    if start.month == end.month:
        return f"{start.strftime(SHORT)}–{end.day}"
    return f"{start.strftime(SHORT)}–{end.strftime(SHORT)}"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def render_html(data: dict, sched: dict, blocks: list[dict], summary: dict, stamp: str) -> str:
    course = data["course"]
    exam = sched["exam_day"]

    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(course['title'])} {esc(course['school_year'])} Calendar</title>",
        f"<style>{CSS}</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        f"<h1>{esc(course['title'])} — Course Calendar</h1>",
        f"<p class=\"sub\">{esc(course['school_year'])} · "
        f"{esc(course.get('district',''))}</p>",
        '<div class="exam">',
        f"<strong>AP Exam: {esc(exam.strftime(LONG))}, {exam.year}</strong>",
        f"<span>{esc(course.get('exam_note',''))}</span>",
        f"<span>{summary['instructional_days_to_exam']} class days from the first "
        f"day of school to the exam</span>",
        "</div>",
        '<div class="legend">',
        '<span class="tag topic">Topic</span>',
        '<span class="tag lab">Lab</span>',
        '<span class="tag assessment">Assessment</span>',
        '<span class="tag flex">Flex</span>',
        '<span class="tag review">Review</span>',
        "<span>Dates shift if school days are lost — check back for updates.</span>",
        "</div>",
    ]

    for block in blocks:
        heading = f"Unit {block['unit']} — {block['title']}" if block["unit"] else block["title"]
        meta = []
        if block["start"] and block["end"]:
            meta.append(date_range_label(block["start"], block["end"]))
        meta.append(f"{sum(e['periods'] for e in block['entries'])} class days")
        if block["weight"]:
            meta.append(f"{block['weight'][0]}–{block['weight'][1]}% of the exam")

        parts.append("<details open>")
        parts.append(
            f"<summary>{esc(heading)}"
            f'<span class="meta">{esc(" · ".join(meta))}</span></summary>'
        )
        parts.append('<div class="rows">')

        for entry in block["entries"]:
            when = date_range_label(entry["start"], entry["end"])
            title = esc(entry["title"])
            if entry["link"]:
                title = f'<a href="{esc(entry["link"])}">{title}</a>'
            # Only CED topic numbers earn a chip — students match those to the
            # textbook. FLEX/PC/TEST/INV ids are internal handles, not content.
            ident = (f'<span class="id">{esc(entry["id"])}</span>'
                     if entry["id"] and entry["kind"] == "topic" else "")

            note_bits = []
            if entry["skill"]:
                note_bits.append(f"Science practice {esc(entry['skill'])}")
            if entry["notes"]:
                note_bits.append(esc(entry["notes"]))
            note = f'<span class="note">{" · ".join(note_bits)}</span>' if note_bits else ""

            parts.append(
                f'<div class="row" data-start="{entry["start"].isoformat()}" '
                f'data-end="{entry["end"].isoformat()}">'
                f'<div class="when">{esc(when)}</div>'
                f'<div class="what"><span class="tag {esc(entry["kind"])}">'
                f'{esc(entry["kind"])}</span> {ident}{title}'
                f'<span class="now-badge">this week</span>{note}</div>'
                "</div>"
            )

        parts.append("</div></details>")

    parts.append(
        f"<footer>Generated {esc(stamp)} from calendar.yaml. "
        f"{summary['published_entries']} scheduled items.</footer>"
    )
    parts.append("</div>")
    parts.append(f"<script>{JS}</script>")
    parts.append("</body></html>")

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    try:
        data = load_source()
        course = data["course"]
        assumptions = data["assumptions"]

        closed = expand_exceptions(data.get("non_instructional_days"), "non_instructional_days")
        testing = expand_exceptions(data.get("site_testing_days"), "site_testing_days")
        all_days = build_day_index(course, closed, testing)
        exam_day = as_date(course["exam_date"], "exam_date")
        pools = build_pools(course, all_days, exam_day)

        sched = schedule(data, all_days, pools)
        blocks = publishable(sched)
    except BuildError as exc:
        print(f"\nBUILD FAILED\n{exc}\n", file=sys.stderr)
        return 1

    exam = sched["exam_day"]
    to_exam = len(sched["pre_days"])
    content_periods = sum(
        e["periods"]
        for b in sched["blocks"]
        for e in b["entries"]
        if e["kind"] in ("topic", "assessment")
    )
    lab_periods = sum(
        e["periods"] for b in sched["blocks"] for e in b["entries"] if e["kind"] == "lab"
    )
    flex_periods = sum(
        e["periods"] for b in sched["blocks"] for e in b["entries"] if e["kind"] == "flex"
    )
    review_periods = sum(
        e["periods"]
        for b in sched["blocks"]
        for e in b["entries"]
        if e["kind"] == "review" and b["phase"] == "spring"
    )
    by_phase = {}
    for b in sched["blocks"]:
        by_phase[b["phase"]] = by_phase.get(b["phase"], 0) + b["periods"]
    lab_obligation = round(to_exam * float(assumptions.get("lab_fraction", 0.25)))

    summary = {
        "instructional_days_total": len(all_days),
        "instructional_days_to_exam": to_exam,
        "instructional_days_after_exam": len(sched["post_days"]),
        "first_instructional_day": iso(all_days[0]),
        "last_instructional_day": iso(all_days[-1]),
        "exam_date": iso(exam),
        "content_periods": content_periods,
        "lab_periods_scheduled": lab_periods,
        "flex_periods": flex_periods,
        "lab_periods_required": lab_obligation,
        "review_periods": review_periods,
        "conversion_factor": assumptions.get("conversion_factor"),
        "labs_additive": assumptions.get("labs_additive"),
        "published_entries": sum(len(b["entries"]) for b in blocks),
    }

    DIST.mkdir(exist_ok=True)
    # Stops GitHub Pages running the output through Jekyll.
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    stamp_local = datetime.now().strftime("%Y-%m-%d %H:%M")
    stamp_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    written = {
        "calendar.json": write_if_changed(
            DIST / "calendar.json",
            render_json(data, sched, blocks, summary, stamp_local)),
        "calendar.ics": write_if_changed(
            DIST / "calendar.ics",
            render_ics(data, sched, blocks, stamp_utc)),
        "index.html": write_if_changed(
            DIST / "index.html",
            render_html(data, sched, blocks, summary, stamp_local)),
    }

    problems = verify_ics(DIST / "calendar.ics")

    hidden = sum(
        1 for b in sched["blocks"] for e in b["entries"] if e["visibility"] == "teacher"
    )

    print(f"AP Biology {course['school_year']} — built {stamp_local}")
    print(f"  instructional days      {len(all_days)}  "
          f"({to_exam} before the exam, {len(sched['post_days'])} after)")
    print(f"  content + assessment    {content_periods} periods")
    pct = round(100 * lab_periods / to_exam) if to_exam else 0
    print(f"  labs scheduled          {lab_periods} periods as dedicated blocks "
          f"({pct}% of days; audit line is 25%)")
    if sched["unscheduled_labs"]:
        print(f"    -> labs_additive is false: {sched['unscheduled_labs']} investigations "
              f"take no dedicated days and are absent from published output.")
    print(f"  in-unit flex days       {flex_periods} periods")
    print(f"  AP review before exam   {review_periods} periods")
    print("  phases                  " + "  ".join(
        f"{k}:{v}" for k, v in by_phase.items()))
    for phase, left in sched["leftovers"].items():
        print(f"    !! {left} unscheduled day(s) left in '{phase}' — "
              f"the calendar has a hole", file=sys.stderr)
    if blocks:
        content_end = max(
            (e["end"] for b in sched["blocks"] for e in b["entries"]
             if e["kind"] in ("topic", "assessment", "lab", "flex") and e["end"]),
            default=None,
        )
        if content_end:
            print(f"  content ends            {content_end.isoformat()}  "
                  f"(exam {exam.isoformat()})")
    if hidden:
        print(f"  teacher-only entries    {hidden} hidden from all published output "
              f"(days still consumed)")
    changed = [name for name, did in written.items() if did]
    if changed:
        print(f"  wrote                   {', '.join('docs/' + c for c in changed)}")
    else:
        print("  wrote                   nothing — output already matches the source")

    if problems:
        print("\n  ICS VALIDATION FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"    - {problem}", file=sys.stderr)
        return 1
    print("  ICS validation          passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
