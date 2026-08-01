# AP Biology 2026-27 course calendar

This repository publishes the calendar. It does not build it.

| | |
|---|---|
| Student page | https://cileapley.github.io/ap-bio-calendar/ |
| Subscribable feed | https://cileapley.github.io/ap-bio-calendar/calendar.ics |
| Raw data | https://cileapley.github.io/ap-bio-calendar/calendar.json |
| Lab prep schedule | https://cileapley.github.io/ap-bio-calendar/prep.html |
| Lab prep feed | https://cileapley.github.io/ap-bio-calendar/prep.ics |

Everything in `docs/` is generated output, pushed here by `publish.py` in the
teaching repository, which is private. Editing a file here changes what students
see until the next publish overwrites it, and changes nothing about the schedule
those files describe.

`calendar.json` is a stable public URL and is meant to be read by other things.
Nothing about its shape is guaranteed across a school year.

Subscribe rather than re-import: event UIDs are stable across rebuilds, so a
topic that moves *moves* in a subscribed calendar instead of duplicating.
