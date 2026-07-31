# AP Biology 2026–27 Course Calendar

One editable source file → a student-facing page, a subscribable feed, and JSON.

```
calendar.yaml   ← the only file you edit
build.py        ← python build.py
docs/           ← generated; don't edit by hand, it gets overwritten
reference/      ← source documents, read-only
```

## Rebuild

```
pip install pyyaml        # once
python build.py
```

The build prints a summary and fails loudly if the sequence no longer fits before
the exam. It also structurally validates the `.ics` before finishing.

## The one rule

**No date is ever typed into the schedule.** Units, topics and labs are counted in
*periods*. `build.py` walks them across the real instructional days it derives from
the district calendar. So:

- Lose a day to an assembly → add it to `site_testing_days`, rebuild, everything
  after it slides one day.
- Unit 3 ran long → change its `periods`, rebuild, Units 4–8 slide.
- Start date moves → change `first_instructional_day`, rebuild, the whole year moves.

You never re-lay-out the calendar by hand. You change one number and rebuild.

## Editing calendar.yaml

### Adding a day off

```yaml
non_instructional_days:
  - {date: 2027-02-19, reason: "Snow day"}
  - {from: 2027-04-05, to: 2027-04-09, reason: "Spring break"}
```

### Site testing days

Not on the district PDF — CAASPP, PSAT, benchmarks, assemblies. Same format,
under `site_testing_days`. These come straight out of your review slack.

### Rebalancing a unit

Change `periods` on any entry. Labs with no `periods` use
`assumptions.default_lab_periods`, so changing that one number rescales every
scheduled investigation at once.

### Moving something

Move the line. Order in the file is order in the year.

### Teacher-only entries

```yaml
- {title: "Pace re-fit checkpoint", periods: 1, kind: topic, visibility: teacher}
```

The entry **still consumes its day** but never appears in `docs/`. That's
deliberate — hiding a block must not silently shift the dates students see.

### `periods: fill`

Takes every remaining day up to the next anchor. The review block uses it, so
whatever it reports *is* your true slack.

### Entry fields

| Field | Meaning |
|---|---|
| `periods` | Class days consumed. Number, or `fill`. |
| `kind` | `topic` · `lab` · `assessment` · `flex` · `review` · `opening` — drives the colour tag |
| `visibility` | `student` (default) or `teacher` |
| `notes` | Shown under the title on the student page |
| `link` | Makes the title a link |
| `skill` | CED science practice code |

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

**`order: 21` is confirmed** — verified against the district's actual
purchase-order turnaround. **`arrive` and `bench` are still defaults from
general lab practice, not vendor data.** Replace them with your supplier's
real kit lead times. Each is one number on one line.

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

## Publishing

`docs/` is served live by GitHub Pages from the `main` branch. There is no
deploy step and no CI:

```
python build.py
git add -A && git commit -m "Update calendar" && git push
```

The site updates within a minute or two. That's the whole workflow.

The build only rewrites a file when the calendar actually changes — timestamps
alone don't count. So if `git status` is empty after a rebuild, nothing about
the schedule moved, and `git diff` always shows real changes rather than churn.

### URLs

| | |
|---|---|
| Student page | `https://cileapley.github.io/ap-bio-calendar/` |
| Subscribable feed | `https://cileapley.github.io/ap-bio-calendar/calendar.ics` |
| Raw data | `https://cileapley.github.io/ap-bio-calendar/calendar.json` |
| Prep schedule (teacher) | `https://cileapley.github.io/ap-bio-calendar/prep.html` |
| Prep feed (teacher) | `https://cileapley.github.io/ap-bio-calendar/prep.ics` |

### Embedding

**Google Sites** — Insert → Embed → *By URL*, paste the student page URL. If
that's blocked, Insert → Embed → *Embed code*:

```html
<iframe src="https://cileapley.github.io/ap-bio-calendar/"
        width="100%" height="900" style="border:0"
        title="AP Biology Calendar"></iframe>
```

**Canvas** — Pages → edit → `</>` HTML editor → same iframe.

### Student subscriptions

Give students the `calendar.ics` URL: Google Calendar → Other calendars →
**From URL**. It re-checks periodically, so a rebuild reaches them without a
re-import. Event UIDs are stable across rebuilds, so a moved topic *moves* in
their calendar rather than duplicating.

### A note on the public repo

This repo is public — that is what makes Pages free. Anyone can read
`calendar.yaml`. `visibility: teacher` keeps an entry off the student page, the
feed and the JSON, but **not** out of the source file. Don't put anything in
here you wouldn't want a student to find.

## What the build reports

```
instructional days      180  (161 before the exam, 18 after)
content + assessment    110 periods
labs scheduled          24 periods as dedicated blocks (15% of days; audit line is 25%)
in-unit flex days       10 periods
AP review before exam   14 periods
lab prep                21 actions across 8 labs — 1 need attention
phases                  fall:83  finals:3  spring:75  post:18
content ends            2027-04-12  (exam 2027-05-03)
```

Read `content ends` first. The gap between it and the exam is what you actually
have for AP review.

The `phases` line must always show every pool fully consumed. If the build warns
that days are left unscheduled in a phase, the calendar has a hole.

## Semester phases

The year is split into four pools, and no block can borrow days across a
boundary:

| Phase | Span | Days | Holds |
|---|---|---|---|
| `fall` | Aug 12 – **Dec 15** | 83 | Opening, Units 1–5 |
| `finals` | Dec 16 – Dec 18 | 3 | Semester 1 finals — off limits to content |
| `spring` | Jan 4 – Apr 30 | 75 | Units 6–8, AP review |
| `post` | May 4 – May 27 | 18 | After the AP exam |

Set by `course.semester_break`:

```yaml
semester_break:
  last_content_day: 2026-12-15   # Unit 5 must finish here
  finals_days: 3                 # the next 3 days are finals
```

Every block declares `phase:`. Move `last_content_day` and the split recomputes.

**This is a tight fit by design.** The fall pool is exactly full, so losing a
single fall day fails the build rather than silently shoving Unit 5 into finals.
That's the intended behaviour — the error names the phase and the entry that
didn't fit, and the flex days in Units 2 and 3 are the release valve.

## How the day budget is built

Everything is **additive**, nothing is carved out of anything else:

| Layer | Days | Source |
|---|---|---|
| Course opening | 3 | editable default |
| Topic instruction | 91 | CED × 0.83, research-adjusted per unit |
| Lab program | 24 | 8 investigations × 3 |
| Assessment | 16 | 2 per unit |
| Semester 1 finals | 3 | off limits |
| Flex | 10 | 1 per unit, 2 in Units 2 and 3 |
| AP review | 14 | whatever is left (`fill`) |
| **Total to May 3** | **161** | |

Assessment and flex days do **not** eat instructional time. Each unit gets its
full content allocation and the test days sit on top.

## Per-unit structure

Every unit ends with the same three days:

```yaml
- {id: "N.FLEX", title: "Flex day — catch-up, reteach, or lab overflow", periods: 1, kind: flex}
- {id: "N.PC",   title: "Progress Check N", periods: 1, kind: assessment}
- {id: "N.TEST", title: "Unit N Assessment", periods: 1, kind: assessment}
```

The flex day sits *before* the assessments deliberately: if the unit ran long you
absorb the overrun there, and if it didn't you get a review day before the test.
Delete the line to reclaim the day; the rest of the year slides back one day.

## The lab program

The [AP Biology Course Audit][audit] requires *"a minimum of 25% of instructional
time engaged in a wide range of hands-on, inquiry-based laboratory
investigations"* **and** *"a minimum of 2 labs per big idea"* — that is 8 named
investigations, not all 13. Teachers may substitute equivalent inquiry-based labs.

Eight are scheduled:

| Big Idea | Scheduled | Unit | |
|---|---|---|---|
| 1 — Evolution | INV-2 Hardy–Weinberg, INV-3 BLAST | 7 | ✅ 2 |
| 2 — Energetics | INV-4 Diffusion & Osmosis, INV-5 Photosynthesis, INV-6 Cellular Respiration | 2, 3 | ✅ 3 |
| 3 — Information Storage | INV-7 Mitosis & Meiosis, INV-8 Bacterial Transformation | 4, 6 | ✅ 2 |
| 4 — System Interactions | INV-13 Enzyme Activity | 3 | 1 |

Big Idea 4 carries one lab rather than two. That's a deliberate call: INV-10
Energy Dynamics was dropped to buy AP review days, and every other spring
investigation is load-bearing for its own big idea — BI1 has both its labs in
Unit 7, and BI3 has one in each semester. If you want a second later, **INV-11
Transpiration at 2 periods in Unit 8** is the cheapest restore.

Five are not scheduled — INV-10, INV-11, INV-12, INV-1 and INV-9. They sit
commented at the bottom of `calendar.yaml` with the reason each was cut and
where to paste it back.

27 dedicated lab days is ~17% of the year. The rest of the 25% audit line is
covered by hands-on work embedded inside topic days — data analysis, modeling,
microscopy, simulations — which is how the requirement is normally satisfied in
practice. The build reports the dedicated percentage for reference, not as a
warning.

## Where the pacing came from

Unit period counts are the CED's, converted to 60-minute periods and then
adjusted against how practising AP Biology teachers actually pace the course.

- **`conversion_factor: 0.83`**, raised from 0.75. A practising teacher's
  published curriculum ([Getting Down with Science][gdws]) restates the CED's
  unit ranges but assumes **50-minute** periods — ~11% more instructional minutes
  than the CED's 45. 45 × 1.11 ÷ 60 = 0.83. This confirms §10 flag 1 of the
  pacing file, which suspected 0.75 was optimistic.
- **Unit 3 gets more than the general uplift.** It is the one unit where
  practitioner pacing diverges sharply: [14–17 fifty-minute classes][gdws-u3]
  against the CED's 12–14 forty-fives, roughly 30% more time, with the note that
  it is *"a tough one… you need to move FAST through some difficult content."*
- **Unit 2** is given ~13 periods of content on the same basis
  ([14–16 fifty-minute classes][gdws-u2]).
- **Unit 6** carries an extra period on Translation — practitioners report
  students *"get stuck with the details of the process of the central dogma."*
- **Unit 7** carries an extra period on Phylogeny; it has the largest exam
  weight and is widely flagged as the hardest unit because it stacks several
  concepts at once.

Every one of these is a commented line in `calendar.yaml`, so you can see and
reverse any of them individually.

## Known gaps, carried forward on purpose

1. **`labs_additive: true`** — the CED never says whether unit period counts
   include lab time. This assumes they don't, which fails safe.
2. **`default_lab_periods: 3`** — a chosen default, not CED guidance. The CED
   declines to allocate at that granularity.
3. **Science practice codes are complete and verified — flag 3 is closed.** All
   60 topic codes were extracted from the official [2025 CED][ced] (Effective
   Fall 2025, updated 6/26, 240pp) and cross-checked against the pacing file's
   independently verified Units 1–3 and 8.1, which matched exactly. Merged topic
   pairs carry the first code of each constituent topic.
4. **Lab titles and numbering are verified — flag 4 is closed.** The pacing file
   flagged these as recalled from memory; all 13 numbers and titles check out
   against the [big-idea listing][labs] and the [Lab Manual Resource Center][lmrc].
5. **May 28, 2027** is not bracketed on the district PDF, but the 11th school month
   is labeled *(9 Days)* and the spring term ends May 27 — which forces it. It's
   after the exam, so it can't affect pacing. Marked as derived in `calendar.yaml`.
6. **AP review is 14 days.** That is the cost of ending Unit 5 at the semester
   break: the fall pool holds 83 days for units that need less, and the spring
   pool absorbs the difference.

## Source documents

- `reference/2026-2027StudentAttendanceCalendar2.2.26.pdf` — Kern High School
  District, adopted 2026-02-02. 180 instructional days; the build reconciles
  against that total.
- `reference/ap-bio-pacing-2026-27.md` — unit, topic and lab sequence.

Both are read-only inputs. `build.py` never touches them.

External sources consulted for the pacing and lab decisions:

[ced]: https://apcentral.collegeboard.org/media/pdf/ap-biology-course-and-exam-description.pdf
[audit]: https://apcentral.collegeboard.org/courses/ap-biology/course-audit
[labs]: https://collegeprep.uworld.com/ap/ap-biology/labs/
[lmrc]: https://apcentral.collegeboard.org/courses/ap-biology/course/lab-manual-resource-center
[gdws]: https://gettingdownwithscience.com/ap-biology-planning-and-pacing/
[gdws-u3]: https://gettingdownwithscience.com/shop/ap-biology-full-curriculum/ap-biology-unit3-cellular-energetics-complete/
[gdws-u2]: https://gettingdownwithscience.com/shop/ap-biology-full-curriculum/ap-biology-unit2-cell-structure-function-complete/

- [AP Biology Course and Exam Description, Effective Fall 2025][ced] — all 60 topic science practice codes
- [AP Biology Course Audit][audit] — the 2-labs-per-big-idea and 25% requirements
- [The 13 investigations by big idea][labs]
- [AP Biology Lab Manual Resource Center][lmrc]
- [Getting Down with Science — planning and pacing][gdws], [Unit 2][gdws-u2], [Unit 3][gdws-u3]
