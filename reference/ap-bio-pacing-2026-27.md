---
title: AP Biology Pacing Map
ced_version: "Effective Fall 2025 (v1)"
school_year: "2026-27"
exam_date: "2027-05-03"
exam_session: "Session 2 (afternoon; 12 p.m. local for lower-48 schools)"
period_model: "60-minute period, 5 days/week"
ced_native_period: "45 minutes"
conversion_factor: 0.75
ced_total_periods_45min_low: 111
ced_total_periods_45min_high: 127
ced_total_periods_60min_low: 83
ced_total_periods_60min_high: 95
derived_total_periods_60min: 89
source: "College Board, AP Biology Course and Exam Description, Effective Fall 2025"
generated: 2026-07-31
revised: 2026-07-31
---

# AP Biology Pacing Map — 2026–27

## 0. What this file is

Unit- and topic-level pacing from the **2025 CED** (effective Fall 2025; first
administered May 2026), converted to **60-minute periods** and expressed as
instructional-day offsets rather than dates, so it can be laid onto whatever
student calendar the generator already holds.

Three tiers of authority in this file, kept deliberately separate:

- **CED-given** — unit-level class period ranges and exam weightings, stated in
  the CED's native 45-minute period. Verbatim. Do not alter.
- **Converted** — the same unit ranges at 60 minutes (× 0.75). Arithmetic only.
- **Derived** — topic-level day allocations. The CED leaves the per-topic class
  period column *blank on purpose* ("The 'class periods' column has been left
  blank so you can customize the time you spend on each topic"). Everything at
  topic granularity below is my distribution of the unit budget, not College
  Board's. Treat as editable defaults.

## 1. Fixed anchors

| Anchor | Value |
|---|---|
| AP Biology exam | **Monday, May 3, 2027**, Session 2 (afternoon) |
| Exam administration window | May 3–7 and May 10–14, 2027 |
| Local period model | **60 min, 5 days/week** |
| CED native period model | 45 min, 5 days/week |
| Lab requirement | 25% of instructional time, hands-on |

**Planning consequence:** AP Biology holds the *first day, first week* slot in
2027. There is no week-2 cushion. Every day of slippage comes out of review.

## 2. Parameters the generator must supply

These are not in this file — pull them from the student calendar / bell schedule:

```yaml
first_instructional_day:   # YYYY-MM-DD
period_minutes: 60
meets_daily: true          # false if the section skips a day in a rotation
non_instructional_days: [] # holidays, PD, finals, testing windows, assemblies
site_testing_days: []      # CAASPP, PSAT, benchmark windows that eat class time
```

Map algorithm: filter the student calendar to instructional days on which the AP
Bio section meets, index them 1..N, then assign unit blocks by the cumulative
day ranges in §5. Anything past the exam date is post-exam programming.

## 3. Unit-level pacing

CED column is verbatim; 60-min column is the CED range × 0.75, rounded to whole
periods.

| Unit | Title | Exam weight | CED (45 min) | Converted (60 min) | Planned |
|---|---|---|---|---|---|
| 1 | Chemistry of Life | 8–11% | ~9–11 | ~7–8 | 7 |
| 2 | Cells | 10–13% | ~14–16 | ~11–12 | 11 |
| 3 | Cellular Energetics | 12–16% | ~12–14 | ~9–11 | 10 |
| 4 | Cell Communication and Cell Cycle | 10–15% | ~12–14 | ~9–11 | 10 |
| 5 | Heredity | 8–11% | ~8–10 | ~6–8 | 7 |
| 6 | Gene Expression and Regulation | 12–16% | ~18–20 | ~14–15 | 14 |
| 7 | Natural Selection | 13–20% | ~19–21 | ~14–16 | 15 |
| 8 | Ecology | 10–15% | ~19–21 | ~14–16 | 15 |
| | **Total** | | **~111–127** | **~83–95** | **89** |

Note the 2025 revision renamed Unit 2 from "Cell Structure and Function" to
**"Cells"**, and topic numbering shifted in Units 2, 4, and 7. If any existing
materials use 2019/2021 topic numbers, they will not line up.

## 4. Topic-level allocation — derived, 60-minute periods

Skill codes are the CED's suggested science practice pairing for that topic
(Progress Check questions are built on these pairings, though exam questions can
pair any skill with any content).

**Topics sharing a period are marked with a brace.** At 60 minutes there aren't
enough days for one topic per day; the pairings below are the ones that survive
compression best, but they're the first thing to re-cut if your run rate differs.

### Unit 1 — Chemistry of Life (7 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 1.1 + 1.2 | Structure of Water and Hydrogen Bonding · Elements of Life | 2.A | 1 |
| 1.3 + 1.4 | Introduction to Macromolecules · Carbohydrates | 2.A, 1.A | 1 |
| 1.5 + 1.6 | Lipids · Nucleic Acids | 6.E, 2.A | 1 |
| 1.7 | Proteins | 6.E | 2 |
| — | Progress Check 1 + unit assessment | — | 2 |

### Unit 2 — Cells (11 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 2.1 | Cell Structure and Function | 1.A, 6.A | 2 |
| 2.2 | Cell Size | 2.D, 5.A | 1 |
| 2.3 + 2.4 | Plasma Membrane · Membrane Permeability | 2.A, 5.D | 1 |
| 2.5 + 2.6 | Membrane Transport · Facilitated Diffusion | 3.D, 6.E | 1 |
| 2.7 | Tonicity and Osmoregulation | 4.A | 2 |
| 2.8 | Mechanisms of Transport | 1.B | 1 |
| 2.9 + 2.10 | Cell Compartmentalization · Origins of Compartmentalization | 6.E, 6.B | 1 |
| — | Progress Check 2 + unit assessment | — | 2 |

2.2 now carries the body-size/metabolic-rate relationship that used to sit in
Unit 8, and it's down to one period here — the tightest squeeze in the file.
Water potential math lives in 2.7; that one kept its two periods deliberately.

### Unit 3 — Cellular Energetics (10 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 3.1 | Enzymes | 1.B, 3.C | 2 |
| 3.2 | Environmental Impacts on Enzyme Function | 6.E | 1 |
| 3.3 | Cellular Energy | 6.C | 1 |
| 3.4 | Photosynthesis | 6.B | 2 |
| 3.5 | Cellular Respiration | 4.A | 2 |
| — | Progress Check 3 + unit assessment | — | 2 |

### Unit 4 — Cell Communication and Cell Cycle (10 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 4.1 + 4.2 | Cell Communication · Introduction to Signal Transduction | — | 1 |
| 4.3 | Signal Transduction Pathways | — | 2 |
| 4.4 | Feedback | — | 2 |
| 4.5 | Cell Cycle | — | 2 |
| 4.6 | Regulation of Cell Cycle | — | 1 |
| — | Progress Check 4 + unit assessment | — | 2 |

Old topics 4.3 and 4.4 were merged into the new 4.3, and everything downstream
renumbered. Six topics now, not seven.

### Unit 5 — Heredity (7 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 5.1 + 5.2 | Meiosis · Meiosis and Genetic Diversity | — | 1 |
| 5.3 | Mendelian Genetics | — | 2 |
| 5.4 | Non-Mendelian Genetics | — | 1 |
| 5.5 | Environmental Effects on Phenotype | — | 1 |
| — | Progress Check 5 + unit assessment | — | 2 |

Smallest unit in the course. Chi-square instruction has to fit inside 5.3/5.4 or
be pre-taught — at seven periods there is no room to teach it cold here.

### Unit 6 — Gene Expression and Regulation (14 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 6.1 | DNA and RNA Structure | — | 1 |
| 6.2 | DNA Replication | — | 2 |
| 6.3 | Transcription and RNA Processing | — | 1 |
| 6.4 | Translation | — | 2 |
| 6.5 | Regulation of Gene Expression | — | 2 |
| 6.6 | Gene Expression and Cell Specialization | — | 1 |
| 6.7 | Mutations | — | 1 |
| 6.8 | Biotechnology | — | 2 |
| — | Progress Check 6 + unit assessment | — | 2 |

### Unit 7 — Natural Selection (15 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 7.1 + 7.2 | Introduction to Natural Selection · Natural Selection | — | 2 |
| 7.3 | Artificial Selection | — | 1 |
| 7.4 | Population Genetics | — | 1 |
| 7.5 | Hardy–Weinberg Equilibrium | — | 3 |
| 7.6 | Evidence of Evolution | — | 1 |
| 7.7 + 7.8 | Common Ancestry · Continuing Evolution | — | 1 |
| 7.9 | Phylogeny | — | 2 |
| 7.10 + 7.11 | Speciation · Variations in Populations | — | 1 |
| 7.12 | Origins of Life on Earth | — | 1 |
| — | Progress Check 7 + unit assessment | — | 2 |

Largest exam weight in the course (13–20%) and the largest Progress Check
(~48 MC in two parts). Hardy–Weinberg keeps three full periods; everything
around it absorbed the compression. Extinction was dropped from this unit in the
2025 CED.

### Unit 8 — Ecology (15 periods)

| Topic | Title | Skill | Periods |
|---|---|---|---|
| 8.1 | Responses to the Environment | 3.C | 1 |
| 8.2 | Energy Flow Through Ecosystems | — | 3 |
| 8.3 | Population Ecology | — | 2 |
| 8.4 | Effect of Density on Populations | — | 2 |
| 8.5 | Community Ecology | — | 2 |
| 8.6 | Biodiversity | — | 2 |
| 8.7 | Disruptions in Ecosystems | — | 1 |
| — | Progress Check 8 + unit assessment | — | 2 |

**8.2 grew in the 2025 CED** — biogeochemical cycles (carbon, water, nitrogen,
phosphorus) were added here, with redundant content trimmed elsewhere to offset.
It keeps three periods for that reason. If you are reusing a pre-2025 Unit 8,
this is the topic that needs building.

## 5. Cumulative instructional-day map (60-min periods)

Contiguous, no slack inserted. Day 0 is a course-opening block, not CED content.

| Block | Days | Cumulative |
|---|---|---|
| Course opening / lab safety / diagnostic | 0 (1–3 days) | — |
| Unit 1 | 1–7 | 7 |
| Unit 2 | 8–18 | 18 |
| Unit 3 | 19–28 | 28 |
| Unit 4 | 29–38 | 38 |
| Unit 5 | 39–45 | 45 |
| Unit 6 | 46–59 | 59 |
| Unit 7 | 60–74 | 74 |
| Unit 8 | 75–89 | 89 |
| Exam review | 90 → exam | — |

Content alone ends around day 89 of ~170. Interleaving the lab program (§7) is
what moves the real finish date; see the budget below before assuming Unit 8
lands in February.

## 6. Period-length conversion reference

Base is now 60 minutes. Multiply the planned column in §3 by these if the
schedule changes:

| Schedule | vs. 60-min base | Content periods | Calendar span |
|---|---|---|---|
| 45-min daily (CED native) | ×1.33 | 119 | ~119 school days |
| **60-min daily (this file)** | **×1.00** | **89** | **~89 school days** |
| 90-min A/B block | ×0.67 | ~59 | ~118 school days |
| 90-min 4×4 (single semester) | ×0.67 | ~59 | ~59 school days |

A 4×4 fall-semester AP Bio finishing in December leaves a four-month gap before
May 3. Budget explicit review sessions if that applies.

## 7. Lab program and the slack budget

25% of instructional time must be hands-on lab work. That is a fraction of the
*calendar*, not of the period length, so it costs the same number of days
regardless of how long a period runs: on a ~170-day year to the exam, **~42–43
periods**.

This is where moving from 45 to 60 minutes actually pays. The content shrinks;
the lab obligation doesn't:

| | 45-min periods | 60-min periods |
|---|---|---|
| CED content (derived) | 119 | 89 |
| Lab program (25% of ~170 days) | ~43 | ~43 |
| **Committed** | **~162** | **~132** |
| Available to May 3 (~170 days) | ~170 | ~170 |
| **Slack** | **~8 days** | **~38 days** |

At 45 minutes the year is effectively full and any disruption eats review. At 60
it isn't. Roughly a month of genuine slack for reteaching, FRQ practice,
site testing days, and April review.

Two caveats on that table. The ~170 figure is a placeholder — compute it from
the actual student calendar (instructional days from day one through May 3,
minus site testing and non-instructional days). And:

**Unresolved:** the CED does not state whether the unit period counts include
lab time. Both readings are defensible:

- *Inclusive* — 89 periods covers content and labs; the lab row above is already
  counted and slack is ~81 days, which is implausibly large.
- *Exclusive* — 89 periods is content only and labs sit on top, as tabulated.

I lean exclusive, because the unit tables are written as topic-coverage
sequences and the CED describes the pacing as covering "the required course
content and... the Progress Checks" without mentioning labs. That is inference
from wording, not a College Board statement. The file assumes exclusive; it
fails safe.

### The 13 investigations

Standard titles from *AP Biology Investigative Labs: An Inquiry-Based Approach*.
Numbering and titles are from memory with partial corroboration — the 2025 CED
cites several by name (Enzyme Lab, Diffusion and Osmosis as Investigation 4,
Transpiration, Fruit Fly Behavior) but I did not verify the full numbered list
against the manual.

| # | Investigation | Unit placement |
|---|---|---|
| 1 | Artificial Selection | 7 (7.3) |
| 2 | Mathematical Modeling: Hardy-Weinberg | 7 (7.5) |
| 3 | Comparing DNA Sequences with BLAST | 7 (7.9) |
| 4 | Diffusion and Osmosis | 2 (2.7) |
| 5 | Photosynthesis | 3 (3.4) |
| 6 | Cellular Respiration | 3 (3.5) |
| 7 | Cell Division: Mitosis and Meiosis | 4/5 (4.5, 5.1) |
| 8 | Biotechnology: Bacterial Transformation | 6 (6.8) |
| 9 | Biotechnology: Restriction Enzyme Analysis | 6 (6.8) |
| 10 | Energy Dynamics | 8 (8.2) |
| 11 | Transpiration | 8 (8.1) |
| 12 | Fruit Fly Behavior | 8 (8.1) |
| 13 | Enzyme Activity | 3 (3.2) |

Loading: Unit 3 carries three labs, Units 7 and 8 three each, Unit 6 two. Unit 1
carries none — a reason to keep Unit 1 tight and bank days early. A 60-minute
period runs most of these in one sitting where a 45 would need two, which is a
second, unquantified gain from the longer period.

## 8. Progress checks

| Unit | MC items | FRQ | FRQ types |
|---|---|---|---|
| 1 | ~24 | 2 | Conceptual Analysis (partial); Analyze Model/Visual Rep (partial) |
| 2 | ~33 (2 parts) | 2 | Interpreting & Evaluating Experimental Results (partial); Analyze Model/Visual Rep (partial) |
| 3 | ~19 | 2 | Interpreting & Evaluating w/ Graphing (partial); Scientific Investigation (partial) |
| 4 | ~24 | 2 | Interpreting & Evaluating (partial); Analyze Data |
| 5 | ~23 | 2 | Interpreting & Evaluating w/ Graphing; Conceptual Analysis |
| 6 | ~25 | 2 | Interpreting & Evaluating; Analyze Model/Visual Rep |
| 7 | ~48 (2 parts) | 2 | Interpreting & Evaluating w/ Graphing; Analyze Data |
| 8 | ~24 | 2 | Interpreting & Evaluating w/ Graphing; Scientific Investigation |

Partial FRQs early in the course scaffold toward full ones; Unit 5 is where they
go full-length.

## 9. Machine-readable block

All `periods` values are 60-minute periods.

```yaml
period_minutes: 60
ced_native_period_minutes: 45
conversion_factor: 0.75

exam:
  date: 2027-05-03
  session: 2
  window: [2027-05-03, 2027-05-14]

units:
  - n: 1
    title: Chemistry of Life
    weight: [8, 11]
    ced_periods_45: [9, 11]
    ced_periods_60: [7, 8]
    planned_periods: 7
    day_start: 1
    day_end: 7
    topics:
      - {id: "1.1+1.2", title: "Water and Hydrogen Bonding / Elements of Life", skill: "2.A", periods: 1}
      - {id: "1.3+1.4", title: "Introduction to Macromolecules / Carbohydrates", skill: "2.A,1.A", periods: 1}
      - {id: "1.5+1.6", title: "Lipids / Nucleic Acids", skill: "6.E,2.A", periods: 1}
      - {id: "1.7", title: "Proteins", skill: "6.E", periods: 2}
      - {id: "1.PC", title: "Progress Check 1 + assessment", periods: 2}
  - n: 2
    title: Cells
    weight: [10, 13]
    ced_periods_45: [14, 16]
    ced_periods_60: [11, 12]
    planned_periods: 11
    day_start: 8
    day_end: 18
    topics:
      - {id: "2.1", title: "Cell Structure and Function", skill: "1.A,6.A", periods: 2}
      - {id: "2.2", title: "Cell Size", skill: "2.D,5.A", periods: 1}
      - {id: "2.3+2.4", title: "Plasma Membrane / Membrane Permeability", skill: "2.A,5.D", periods: 1}
      - {id: "2.5+2.6", title: "Membrane Transport / Facilitated Diffusion", skill: "3.D,6.E", periods: 1}
      - {id: "2.7", title: "Tonicity and Osmoregulation", skill: "4.A", periods: 2}
      - {id: "2.8", title: "Mechanisms of Transport", skill: "1.B", periods: 1}
      - {id: "2.9+2.10", title: "Cell Compartmentalization / Origins", skill: "6.E,6.B", periods: 1}
      - {id: "2.PC", title: "Progress Check 2 + assessment", periods: 2}
  - n: 3
    title: Cellular Energetics
    weight: [12, 16]
    ced_periods_45: [12, 14]
    ced_periods_60: [9, 11]
    planned_periods: 10
    day_start: 19
    day_end: 28
    topics:
      - {id: "3.1", title: "Enzymes", skill: "1.B,3.C", periods: 2}
      - {id: "3.2", title: "Environmental Impacts on Enzyme Function", skill: "6.E", periods: 1}
      - {id: "3.3", title: "Cellular Energy", skill: "6.C", periods: 1}
      - {id: "3.4", title: "Photosynthesis", skill: "6.B", periods: 2}
      - {id: "3.5", title: "Cellular Respiration", skill: "4.A", periods: 2}
      - {id: "3.PC", title: "Progress Check 3 + assessment", periods: 2}
  - n: 4
    title: Cell Communication and Cell Cycle
    weight: [10, 15]
    ced_periods_45: [12, 14]
    ced_periods_60: [9, 11]
    planned_periods: 10
    day_start: 29
    day_end: 38
    topics:
      - {id: "4.1+4.2", title: "Cell Communication / Introduction to Signal Transduction", periods: 1}
      - {id: "4.3", title: "Signal Transduction Pathways", periods: 2}
      - {id: "4.4", title: "Feedback", periods: 2}
      - {id: "4.5", title: "Cell Cycle", periods: 2}
      - {id: "4.6", title: "Regulation of Cell Cycle", periods: 1}
      - {id: "4.PC", title: "Progress Check 4 + assessment", periods: 2}
  - n: 5
    title: Heredity
    weight: [8, 11]
    ced_periods_45: [8, 10]
    ced_periods_60: [6, 8]
    planned_periods: 7
    day_start: 39
    day_end: 45
    topics:
      - {id: "5.1+5.2", title: "Meiosis / Meiosis and Genetic Diversity", periods: 1}
      - {id: "5.3", title: "Mendelian Genetics", periods: 2}
      - {id: "5.4", title: "Non-Mendelian Genetics", periods: 1}
      - {id: "5.5", title: "Environmental Effects on Phenotype", periods: 1}
      - {id: "5.PC", title: "Progress Check 5 + assessment", periods: 2}
  - n: 6
    title: Gene Expression and Regulation
    weight: [12, 16]
    ced_periods_45: [18, 20]
    ced_periods_60: [14, 15]
    planned_periods: 14
    day_start: 46
    day_end: 59
    topics:
      - {id: "6.1", title: "DNA and RNA Structure", periods: 1}
      - {id: "6.2", title: "DNA Replication", periods: 2}
      - {id: "6.3", title: "Transcription and RNA Processing", periods: 1}
      - {id: "6.4", title: "Translation", periods: 2}
      - {id: "6.5", title: "Regulation of Gene Expression", periods: 2}
      - {id: "6.6", title: "Gene Expression and Cell Specialization", periods: 1}
      - {id: "6.7", title: "Mutations", periods: 1}
      - {id: "6.8", title: "Biotechnology", periods: 2}
      - {id: "6.PC", title: "Progress Check 6 + assessment", periods: 2}
  - n: 7
    title: Natural Selection
    weight: [13, 20]
    ced_periods_45: [19, 21]
    ced_periods_60: [14, 16]
    planned_periods: 15
    day_start: 60
    day_end: 74
    topics:
      - {id: "7.1+7.2", title: "Introduction to Natural Selection / Natural Selection", periods: 2}
      - {id: "7.3", title: "Artificial Selection", periods: 1}
      - {id: "7.4", title: "Population Genetics", periods: 1}
      - {id: "7.5", title: "Hardy-Weinberg Equilibrium", periods: 3}
      - {id: "7.6", title: "Evidence of Evolution", periods: 1}
      - {id: "7.7+7.8", title: "Common Ancestry / Continuing Evolution", periods: 1}
      - {id: "7.9", title: "Phylogeny", periods: 2}
      - {id: "7.10+7.11", title: "Speciation / Variations in Populations", periods: 1}
      - {id: "7.12", title: "Origins of Life on Earth", periods: 1}
      - {id: "7.PC", title: "Progress Check 7 + assessment", periods: 2}
  - n: 8
    title: Ecology
    weight: [10, 15]
    ced_periods_45: [19, 21]
    ced_periods_60: [14, 16]
    planned_periods: 15
    day_start: 75
    day_end: 89
    topics:
      - {id: "8.1", title: "Responses to the Environment", skill: "3.C", periods: 1}
      - {id: "8.2", title: "Energy Flow Through Ecosystems", periods: 3}
      - {id: "8.3", title: "Population Ecology", periods: 2}
      - {id: "8.4", title: "Effect of Density on Populations", periods: 2}
      - {id: "8.5", title: "Community Ecology", periods: 2}
      - {id: "8.6", title: "Biodiversity", periods: 2}
      - {id: "8.7", title: "Disruptions in Ecosystems", periods: 1}
      - {id: "8.PC", title: "Progress Check 8 + assessment", periods: 2}

labs:
  requirement_fraction: 0.25
  basis: calendar_days          # 25% of instructional days, not of period minutes
  assume_additive_to_unit_periods: true
  estimated_periods: 43
  investigations:
    - {n: 1,  title: "Artificial Selection", unit: 7, topic: "7.3"}
    - {n: 2,  title: "Mathematical Modeling: Hardy-Weinberg", unit: 7, topic: "7.5"}
    - {n: 3,  title: "Comparing DNA Sequences with BLAST", unit: 7, topic: "7.9"}
    - {n: 4,  title: "Diffusion and Osmosis", unit: 2, topic: "2.7"}
    - {n: 5,  title: "Photosynthesis", unit: 3, topic: "3.4"}
    - {n: 6,  title: "Cellular Respiration", unit: 3, topic: "3.5"}
    - {n: 7,  title: "Cell Division: Mitosis and Meiosis", unit: 4, topic: "4.5"}
    - {n: 8,  title: "Biotechnology: Bacterial Transformation", unit: 6, topic: "6.8"}
    - {n: 9,  title: "Biotechnology: Restriction Enzyme Analysis", unit: 6, topic: "6.8"}
    - {n: 10, title: "Energy Dynamics", unit: 8, topic: "8.2"}
    - {n: 11, title: "Transpiration", unit: 8, topic: "8.1"}
    - {n: 12, title: "Fruit Fly Behavior", unit: 8, topic: "8.1"}
    - {n: 13, title: "Enzyme Activity", unit: 3, topic: "3.2"}
```

## 10. Sources and confidence

**Verified against the primary source** (College Board, *AP Biology Course and
Exam Description*, Effective Fall 2025, fetched 2026-07-31 from
apcentral.collegeboard.org): unit titles, exam weightings, unit class period
ranges, full topic list and numbering, suggested science practice skills for
Units 1–3 and topic 8.1, Progress Check composition, the 25% lab requirement,
and the 45-minute/5-day period model.

**Verified against AP Central exam dates page:** May 3, 2027, Session 2.

**Flags:**

1. *The 60-minute figures are arithmetic, not College Board guidance.* The CED
   states pacing only in 45-minute periods. Multiplying by 0.75 assumes a
   60-minute period delivers proportionally more content than a 45, which is
   optimistic — transitions, warm-ups, and pack-up are roughly fixed costs, so
   real throughput on a 60 is probably nearer 1.25× a 45 than 1.33×. If that is
   right, planned totals should be ~95 rather than 89. Track actual pace through
   Units 1–2 and re-fit before Unit 6.

2. *Units 7 and 8 both read ~19–21 class periods in the CED.* That came out of
   the Course at a Glance table. It is plausible — the 2019 CED had Unit 7 at
   ~20–23 and Unit 8 at ~18–21 — but two identical ranges in adjacent rows is
   the shape a text-extraction error takes. The exam weightings on those rows
   extracted correctly and differ, which argues against duplication, and the
   Units 1–3 numbers from that same table matched their unit-opener pages
   exactly. Spot-check pages 125 and 147 of your CED copy anyway.

3. *Suggested skills are blank for Units 4–7.* The CED assigns one to every
   topic; the fetch truncated before those tables. Fill from your copy if the
   calendar needs them.

4. *Lab titles and numbering are from memory,* with the CED corroborating four
   of the thirteen by name. Check against the Lab Manual Resource Center.

5. *Whether unit periods include lab time is unresolved* — see §7. Along with
   flag 1, the largest source of error in any layout built from this file.

6. *All topic-level day counts and all topic pairings are mine, not College
   Board's.* The CED deliberately declines to allocate at that granularity.
