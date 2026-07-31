# Calendar change report — design

**Date:** 2026-07-31
**Status:** approved, not yet implemented
**Affects:** new `changes.py`, new `tests/test_changes.py`, `.gitignore`, `README.md`

---

## Problem

The calendar moved twice today. Labs went from three days to two, which resized
eight entries and shifted three spring units. Nothing announced what changed.

Two consumers need to know, and neither is served today:

**The lesson-plan workspace** (`ws/lesson plans`, writing to `ws/teaching/apb/`)
keys 107 lesson plans to this calendar's entry ids and day indices. Its spec
pins `docs/calendar.json` by SHA256. A hash tells it *that* the file changed,
never *what* — so after a change it can only re-derive everything or trust that
nothing important moved. When `INV-4` dropped from three days to two, the plan
keyed to its third day was orphaned with no signal.

**The teacher** needs to tell students when a date slips. `git diff` on a
35 KB JSON file does not answer "what moved?"

## Non-goals

- **Not a gate.** A changed calendar is never an error. This reports; it does
  not block a build or a commit.
- **Not a lesson-plan validator.** The lesson-plan workspace owns its own
  validation and has already designed the join. Building a second checker here
  would put two things in charge of one contract.
- **Not integrated into `build.py`.** `build.py` has no git dependency today and
  runs in a fresh clone or an unzipped folder. That property is worth keeping.
- **Not a general JSON differ.** It understands this calendar's shape only.

## Approach

A standalone `changes.py`, split the way `prep.py` and `build.py` already split:
a pure function that diffs two parsed calendars, and a thin CLI that supplies
them.

Rejected alternatives:

- **Fold into `build.py`** — zero friction, since a rebuild happens anyway, but
  it couples the build to git and adds to a file already past 800 lines.
- **Pre-commit hook** — automatic but invisible. The wrong kind of magic for a
  repository a teacher maintains during a school year.

---

## Interface

```python
diff(old: dict, new: dict) -> list[EntryDelta]
```

Pure. Takes two parsed `calendar.json` documents, returns entry-level deltas
ordered by severity. No I/O, no git, no clock. Tests construct dicts by hand.

```python
@dataclass(frozen=True)
class EntryDelta:
    entry_id: str                    # id, or "block_id:title" when id is null
    kind: str                        # topic | lab | assessment | flex | review | opening
    title: str                       # current title; old title when removed
    changes: tuple[str, ...]         # subset of REMOVED/RESIZED/MOVED/ADDED/RETITLED
    old: dict | None                 # {periods, start, end, title}; None when added
    new: dict | None                 # same shape; None when removed
    lost_day_indices: tuple[int, ...]
```

### Identity

Entries match on `id`. Four of the 85 have none — the course-opening block and
the two `fill` review blocks — and those match on `f"{block_id}:{title}"`, which
is stable for them. None is a `topic` or `lab`, so none can orphan a lesson plan.

Matching on position was rejected: inserting one entry would renumber everything
after it and report the whole year as changed.

### One delta per entry

An entry that both moved and shrank produces a single record carrying
`("MOVED", "RESIZED")`. Emitting one record per change type would double-count
in the summary and make the counts misleading.

### Lost days stay convention-free

When `periods` shrinks, `lost_day_indices` carries the raw indices that no longer
exist — `(3,)` for a three-day entry that became two.

It does **not** carry formatted keys like `INV-4-d3`. The lesson-plan workspace's
spec says only that "the calendar join key lives in frontmatter"; the `{id}-d{n}`
format was this author's suggestion, not their published contract. Baking a
guess at another project's key format into this one's output would make the two
silently disagree the moment they diverge. The human summary renders `INV-4-d3`
as a readability hint; the machine output stays neutral.

Growth produces no lost indices — a longer entry orphans nothing.

---

## Change types

| Type | Condition | Why it matters |
|---|---|---|
| `REMOVED` | id present in old, absent in new | Every plan for it is orphaned |
| `RESIZED` | `periods` differs | Shrinking orphans the trailing days. This is the case that earns the tool — it fired eight times today |
| `MOVED` | `start` differs, or `end` differs while `periods` is unchanged | What the teacher tells students |
| `ADDED` | id absent in old, present in new | Needs plans written |
| `RETITLED` | `title` differs | Lesson-plan frontmatter copies the title, so a rename desyncs it silently |

Ordered by consequence. A removal loses work; a retitle is cosmetic.

The `MOVED` condition is deliberately not "start or end differs". Shrinking a
three-day entry to two changes its end date as a direct consequence of the
resize, and reporting that as a move as well would flag every resized entry
twice. Requiring `periods` to be unchanged isolates the case that is genuinely a
move on its own: an entry that kept its length but slid, which is what happens
when a holiday is inserted before or inside it.

---

## Outputs

**Human summary to stdout**, grouped by change type in the order above. Shape of
the output — counts and dates below are illustrative, not a prediction:

```
Calendar changes vs HEAD

RESIZED  8 entries
  INV-4    Investigation 4 — Diffusion and Osmosis    3 days -> 2   orphans INV-4-d3
  INV-13   Investigation 13 — Enzyme Activity         3 days -> 2   orphans INV-13-d3

MOVED  3 entries
  6.4      Translation                                Jan 20-22 -> Jan 19-21

Nothing added, removed or retitled.
```

**Machine JSON to `changes.json` at the repository root**, gitignored.

It must not be committed. If it lived in `docs/` and were committed, the next
build's diff against HEAD would be empty, which would change `changes.json`
again — a feedback loop leaving the tree permanently dirty.

The root, not `docs/`: `docs/` is what GitHub Pages publishes, and this is
working state rather than published output.

---

## Failure behaviour

Follows the repository's existing warn-versus-fail line: structural problems
fail, facts about the world are reported.

| Situation | Behaviour | Exit |
|---|---|---|
| Not a git repository | "No git baseline to compare against." | 0 |
| No `docs/calendar.json` in HEAD | Same — nothing published yet | 0 |
| `docs/calendar.json` missing in the working tree | "Run `python build.py` first." | 1 |
| Either file unparseable | Name the file and the parse error | 1 |
| Any set of changes, including none | Report them | 0 |

A changed calendar is never an error.

---

## Verification

`unittest`, standard library only, consistent with the rest of the repository.
Every case exercises pure `diff()` against hand-built dicts, so no test needs
git, the filesystem, or a build.

1. Identical calendars produce no deltas.
2. `periods` 3 → 2 yields `RESIZED` with `lost_day_indices == (3,)`.
3. `periods` 3 → 1 yields `lost_day_indices == (2, 3)`.
4. `periods` 2 → 3 yields `RESIZED` with **no** lost indices.
5. A changed `start` yields `MOVED`.
6. An id present only in the new calendar yields `ADDED`, with `old is None`.
7. An id present only in the old calendar yields `REMOVED`, with `new is None`.
8. A changed `title` yields `RETITLED`.
9. An entry that both moved and resized yields **one** delta carrying both.
10. An id-less entry matches on `block_id:title` across builds and is not
    reported as removed-and-added.
11. Deltas come back ordered by severity, removals first.

**Real-data check**, run once by hand after implementation: `git stash` the
current calendar, revert `default_lab_periods` to 3, rebuild, run the report,
and confirm it names the eight resized investigations and their lost third days.
That change is the motivating case and the tool should describe it exactly.

---

## Follow-on work, out of scope

- Publishing a change feed students could subscribe to. Different audience,
  different cadence, and it would need a stable notion of "announced" versus
  "not yet announced" that this design deliberately avoids.
- Comparing arbitrary git revisions rather than HEAD. Straightforward to add
  later; not needed for the question "what will this commit change?"
