# Lab prep lead times — design

**Date:** 2026-07-31
**Status:** approved, not yet implemented
**Affects:** `calendar.yaml`, `build.py`, `docs/` (two new outputs)

---

## Problem

Eight AP Biology investigations are scheduled across 2026–27. Each needs work
done well before its lab day: a purchase order submitted, materials delivered,
and bench prep started. Those windows are invisible on the current calendar, and
missing one means the lab does not happen.

The failure mode is not miscalculating a date. It is **not looking on the right
day**. Any solution that requires remembering to check something has not solved
the problem.

The motivating case is **INV-8 Bacterial Transformation** (lab Jan 26): its naive
arrival date lands inside Christmas recess, so the real deadline is earlier than
the arithmetic suggests. Naive date subtraction is wrong in ways that are easy to
miss and expensive to get wrong.

An initial six-week purchase-order assumption also put INV-4's order date before
the first day of school. The teacher has since confirmed the district turns
purchase orders around **faster than six weeks**, which moves that date into term
and removes the alarm. The exact cycle length is not yet known; see *Default lead
times* below.

## Non-goals

- **Not** a lesson-plan parser. No structured lesson plans exist yet; extracting
  assignments from prose would mean inventing the source first.
- **Not** collaborative editing. The second AP Biology teacher consumes the
  published calendar rather than co-editing it, so the published URL already
  solves distribution.
- **Not** an assignments-and-due-dates layer. That may come later and would hang
  off the same entry IDs, but it is a separate piece of work.
- **Not** room or equipment booking. Explicitly excluded by the teacher.

## Approach

Lead times live inline on each lab entry in `calendar.yaml`. `build.py` derives
prep dates by subtracting them from the lab's first scheduled day and emits two
new teacher-facing outputs.

This preserves the project's central rule: **no date is ever typed in**. Prep
dates are derived, so when a unit slips they slip with it — the same guarantee
every other date in the system already has.

Two alternatives were considered and rejected:

- **Separate `labs.yaml` joined at build time.** Cleaner separation if lab
  material lists grow large, but at eight labs the join costs more than it buys
  and introduces a second file to keep in sync.
- **Terminal output only.** Half the work, but it fails the actual requirement:
  you would only see prep dates when you happen to rebuild, which is not six
  weeks before a PO is due.

---

## Data model

Each lab entry gains an optional `prep:` mapping:

```yaml
- {id: "INV-8", title: "Investigation 8 — Biotechnology: Bacterial Transformation",
   kind: lab, notes: "Big Idea 3: Information Storage and Transmission.",
   prep: {order: 42, arrive: 7, bench: 3}}
```

Three keys, each with a **fixed basis** chosen to match how that step actually
works. No suffixes or per-value syntax.

| Key | Meaning | Counted in | Then |
|---|---|---|---|
| `order` | Submit the purchase order by this date | **calendar** days — purchasing runs over breaks | snap backward to an instructional day |
| `arrive` | Materials must be in the building | **calendar** days — shipping runs on calendar time | snap backward to an instructional day |
| `bench` | Start hands-on prep | **school** days — prep happens on school days | already a school day |

All three subtract from the lab's **first** day, not its last.

Any key may be omitted. A lab with no `prep:` block produces no prep actions.

### Why the bases differ

Purchasing and shipping run on calendar time and do not pause for Thanksgiving.
Bench prep is work a person does at school, so counting it in school days is what
a teacher actually means by "start prep three days before."

### Why snapping is backward only

Snapping never moves a deadline later. A date that lands on a Saturday or inside
a recess is snapped to the last instructional day at or before it. This is
conservative by construction: the computed date is always achievable or flagged,
never optimistically late.

Snapping is what makes INV-8 correct. Its naive `arrive` date falls inside
Christmas recess; snapping moves it back to Dec 18, and because the snap crossed
a break by more than two days, the build flags that the effective deadline moved.

### Early-and-late-both-fail cases

`arrive` handles perishables. INV-5 Photosynthesis needs fresh spinach, so its
`arrive` is 3 days rather than two weeks — while INV-6 Cellular Respiration needs
peas soaked and germinating, so its `bench` is long and its `arrive` early. The
two labs are nine days apart and want opposite treatment.

---

## Outputs

Two new files, both derived, both teacher-facing.

| File | Contents |
|---|---|
| `docs/prep.html` | Every prep action for the year in one chronological list, grouped by month, each showing its lab, its action, and how many days out. Self-contained: inline CSS, no network requests, same constraints as the student page. |
| `docs/prep.ics` | Subscribable feed, one all-day event per action. Summary format: `Order: Investigation 8 materials (lab Jan 26)`. Stable UIDs of the form `prep-{labid}-{action}@apbio-2026-27`. |

The `.ics` is the part that solves the stated problem: it puts the deadline in
the calendar the teacher already checks, rather than in a page they must remember
to open.

### Isolation from student output

`index.html`, `calendar.ics` and `calendar.json` are unchanged. Prep data appears
in none of them. This is enforced by an explicit leak test, the same shape as the
existing `visibility: teacher` exclusion test.

Note: the repository is public, so `prep.html` is publicly reachable. Nothing in
it is sensitive. This is recorded so it is a known property rather than a
surprise.

---

## Warnings and errors

The project's existing convention is followed: **structural contradictions fail
the build; judgment calls warn.**

| Condition | Behaviour | Rationale |
|---|---|---|
| Prep date is in the past | Warn | A fact about today, not a broken calendar. Failing here would make the build unusable for the rest of the year. |
| Prep date precedes the first instructional day | Warn | Actionable — it means the task belongs to the summer. |
| Snapping crossed a break by more than 2 days | Warn | The effective deadline moved earlier than the arithmetic implies. |
| `arrive` is earlier than `order` | **Fail** | The lead times contradict each other. An authoring error, like a phase overrun. |

Warnings print to stderr and name the lab, the action and the gap in days.

The build summary gains one line:

```
lab prep              21 actions across 8 labs — 2 need attention
```

---

## Default lead times

These are **defaults chosen from general lab practice, not vendor data and not
from any supplier catalogue.** They are commented in `calendar.yaml` and are
expected to be overridden once real PO cycles and kit lead times are known.

| Lab | Lab date | `order` | `arrive` | `bench` | Reasoning |
|---|---|---|---|---|---|
| INV-4 Diffusion & Osmosis | Sep 15 | 21 | 14 | 2 | Dialysis tubing and sucrose store well |
| INV-13 Enzyme Activity | Oct 2 | 21 | 7 | 2 | H₂O₂ degrades; do not buy far ahead |
| INV-5 Photosynthesis | Oct 14 | 21 | 3 | 1 | Spinach must be fresh — equipment early, produce late |
| INV-6 Cellular Respiration | Oct 23 | 21 | 14 | 5 | Peas need soaking then germinating; longest bench |
| INV-7 Mitosis & Meiosis | Nov 16 | 21 | 14 | 5 | Onion root tips take about a week to grow |
| INV-8 Bacterial Transformation | Jan 26 | 28 | 7 | 3 | Competent cells are cold-chain and short-lived; kit ordering is slower |
| INV-2 Hardy–Weinberg | Feb 16 | 14 | — | 1 | Beads or a spreadsheet |
| INV-3 BLAST | Feb 26 | — | — | 1 | Computers only; this one books the cart |

21 prep actions total.

`order` defaults to **21 days (three weeks)**, down from an initial 42. The
teacher confirmed the district's purchase-order cycle is shorter than six weeks
but has not yet supplied the exact figure; 21 is a deliberate placeholder that
keeps every order date inside term. INV-8 keeps 28 because kit ordering with
cold-chain shipping is slower than consumables.

The single highest-value correction to this file is the real PO cycle length.
Changing it is one number per lab, and the build reports immediately if a new
value pushes a date into the past or before the first day of school.

**This table is the largest source of error in the feature.** The mechanism will
be correct; whether 42 days matches the district PO cycle, or 5 days is enough to
germinate peas, is domain knowledge the teacher holds. Each value is one number
on one line, and the build reports immediately when a change pushes a date into
the past.

---

## Verification

Following the patterns already in the repository.

**Build-time assertions**

- Every prep date is on or before its lab's first day.
- `arrive` is on or after `order` for every lab that declares both.
- Every prep date is an instructional day, or is explicitly flagged as preceding
  the first day of school.

**Tests**

1. **Leak test** — no prep string appears in `index.html`, `calendar.ics` or
   `calendar.json`.
2. **ICS structural validation** — `prep.ics` passes the existing `verify_ics()`
   check: CRLF endings, lines within 75 octets, balanced components, required
   properties, parseable dates.
3. **Independent cross-check** — the standalone verify script confirms every prep
   date against the instructional-day set derived directly from the district PDF,
   so no part of the system validates itself.
4. **Cascade test** — shift a unit by one week, confirm every prep date moves
   with it, revert, confirm output is byte-identical.
5. **Known-case test** — INV-8's `arrive` snaps out of Christmas recess and
   raises the break-crossing warning. The past-date and before-term warnings are
   tested by temporarily raising an `order` value rather than relying on the
   current defaults, which no longer trigger them. All date-sensitive tests must
   pin a build date rather than use today's, so they do not change behaviour as
   the year progresses.

**Non-regression**

The existing seven acceptance criteria continue to pass unchanged, including the
no-op rebuild producing no diff.

---

## Open questions

None blocking. Two were raised during design and resolved:

- **Vocabulary.** `order` / `arrive` / `bench` was confirmed sufficient; no
  separate quote or requisition step is needed.
- **Snapping.** Backward-only to an instructional day was confirmed correct.
  It applies to `order` and `arrive`, which are counted in calendar days and can
  therefore land on a weekend or in a recess. `bench` is counted in school days
  and is already on an instructional day by construction, so snapping is a no-op
  for it — the rule is stated uniformly but only bites on two of the three keys.

## Follow-on work, explicitly out of scope

- An assignments-and-due-dates layer hanging off the same entry IDs, using the
  currently unused `link:` field.
- Materials lists per investigation, if `prep.html` should become a shopping
  list rather than a schedule.
- Restoring INV-11 Transpiration for Big Idea 4. **Decided against for now** —
  the teacher is not treating the two-labs-per-big-idea line as binding, so the
  warnings about it have been removed from the README and `calendar.yaml`. If it
  is restored later it inherits prep actions automatically from its `prep:`
  block, so nothing here needs to change to accommodate it.
