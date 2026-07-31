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


def ics_escape(text: str) -> str:
    return (str(text).replace("\\", "\\\\")
                     .replace(";", "\\;")
                     .replace(",", "\\,")
                     .replace("\n", "\\n"))


def fold(line: str) -> list[str]:
    """RFC 5545 folding. Split on octet length so multibyte text stays legal."""
    raw = line.encode("utf-8")
    if len(raw) <= 73:
        return [line]
    out, current, size = [], "", 0
    for char in line:
        width = len(char.encode("utf-8"))
        limit = 73 if not out else 72          # continuation lines carry a space
        if size + width > limit:
            out.append(current)
            current, size = "", 0
        current += char
        size += width
    if current:
        out.append(current)
    return [out[0]] + [" " + part for part in out[1:]]


def calendar_header(name: str, prodid_tag: str) -> list[str]:
    """The VCALENDAR preamble, folded and escaped.

    Both feeds build the same seven lines. Keeping one copy is not tidiness:
    the duplicated version has already produced two defects in these exact
    lines — unfolded output, then unescaped PRODID.

    `name` becomes X-WR-CALNAME. `prodid_tag` distinguishes the feeds inside
    PRODID. Both are escaped; every line is folded.
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{ics_escape(name)}//{ics_escape(prodid_tag)}//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(name)}",
        "X-PUBLISHED-TTL:PT12H",
    ]
    out: list[str] = []
    for line in lines:
        out.extend(fold(line))
    return out


def slug(*parts) -> str:
    joined = "-".join(str(p) for p in parts if p)
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9]+", "-", joined)).strip("-").lower()


def verify_ics(path: Path) -> list[str]:
    """Structural check with the standard library only. Returns problems found."""
    problems: list[str] = []
    raw = path.read_bytes()

    if b"\r\n" not in raw:
        problems.append("file does not use CRLF line endings")
    if re.search(rb"(?<!\r)\n", raw):
        problems.append("found a bare LF not preceded by CR")

    text = raw.decode("utf-8")
    physical = text.split("\r\n")
    if physical and physical[-1] == "":
        physical.pop()

    for number, line in enumerate(physical, 1):
        if len(line.encode("utf-8")) > 75:
            problems.append(f"line {number} exceeds 75 octets")

    # Unfold before checking structure.
    logical: list[str] = []
    for line in physical:
        if line.startswith((" ", "\t")) and logical:
            logical[-1] += line[1:]
        else:
            logical.append(line)

    stack: list[str] = []
    events = 0
    for line in logical:
        if line.startswith("BEGIN:"):
            stack.append(line[6:])
        elif line.startswith("END:"):
            if not stack or stack[-1] != line[4:]:
                problems.append(f"unbalanced END:{line[4:]}")
            else:
                if stack[-1] == "VEVENT":
                    events += 1
                stack.pop()
        elif line and ":" not in line and ";" not in line:
            problems.append(f"line is not a property: {line[:40]!r}")
    if stack:
        problems.append(f"unclosed component(s): {stack}")

    if logical[:1] != ["BEGIN:VCALENDAR"] or logical[-1:] != ["END:VCALENDAR"]:
        problems.append("file is not wrapped in BEGIN/END:VCALENDAR")
    for required in ("VERSION:2.0", "CALSCALE:GREGORIAN"):
        if required not in logical:
            problems.append(f"missing required property {required}")

    # Every VEVENT needs UID, DTSTAMP, DTSTART, SUMMARY, and valid dates.
    current: dict[str, str] = {}
    inside = False
    for line in logical:
        if line == "BEGIN:VEVENT":
            inside, current = True, {}
        elif line == "END:VEVENT":
            for required in ("UID", "DTSTAMP", "DTSTART", "SUMMARY"):
                if not any(k == required or k.startswith(required + ";") for k in current):
                    problems.append(f"VEVENT {current.get('UID', '?')} missing {required}")
            for key, value in current.items():
                if key.startswith("DTSTART") or key.startswith("DTEND"):
                    try:
                        datetime.strptime(value, "%Y%m%d")
                    except ValueError:
                        problems.append(f"VEVENT {current.get('UID', '?')} has bad date {value!r}")
            inside = False
        elif inside and ":" in line:
            key, value = line.split(":", 1)
            current[key] = value

    if events == 0:
        problems.append("no VEVENTs written")
    return problems
