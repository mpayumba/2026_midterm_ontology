# 2026 Midterm Ontology

A structured, legally grounded model of every U.S. House and Senate contest
in the 2026 cycle — 470 contests — rendered as an interactive map with a
point query ("what's on the ballot at this location?") and a contest detail
view.

This is **not a CRUD app over an elections table**. It is an ontology with a
UI, and the code enforces the ontology's commitments.

## The ontology

### Contest is the central entity

A **Contest** is the process of filling one **Term** of one **Seat**. What
voters casually call "an election" is three distinct things, never conflated:

| Thing | What it is | In the code |
|---|---|---|
| Election | a state-administered event on a date | `administered_by` + stage `election_date`s |
| Contest | the process of filling one term of one seat | `Contest` |
| ContestStage | the contest's appearance in one administered election | `ContestStage` (primary, runoff, general) |

Every view in the app is a projection of the contest set.

### Three layers, kept typed apart

1. **Structural (de jure)** — seats, district plans, terms, legal citations.
   Grounded in legal instruments via `LegalCitation` edges: Art. I § 3 cl. 2
   for Senate class staggering, the 17th Amendment + state statute for
   vacancy appointments, state election code for primary scheduling, the
   enacting authority for each district plan.
2. **Event (de facto)** — contests, stages, candidacies, vacancies: the 2026
   cycle as time-indexed assertions over the structural layer.
3. **Epistemic** — ratings/forecasts are `Annotation` objects (source +
   timestamp): credences *about* contests, never fields on them. The UI
   renders them in a visually distinct "Assessments" section. `PROJECTED`
   (a media call) and `CERTIFIED` (the legal truth-maker) are distinct
   lifecycle states.

### Derived facts are functions, never stored fields

If it is a theorem of the ontology, it is a function in the code:

- *"Is this seat up in 2026?"* — `is_up_in(seat, cycle, vacancies)`,
  computed from Senate class staggering (`senate_class_up_in`, anchored on
  Class 2 elected 2020 ⇒ up 2026) + vacancy events. The registry **derives**
  the 33 regular Senate contests from the 100-seat class table; nothing is
  hand-listed.
- *"Is this an open seat?"* — `is_open_seat(contest)`, computed from
  candidacy incumbency records.
- Majority arithmetic — `net_seats_to_flip(...)`, computed from occupancy.

### Seats are a discriminated union

`SenateSeat` is individuated by (state, class); `HouseSeat` by (state,
district_number, with 0 = at-large). A Senate contest's constituency is the
state division directly — it has **no district or plan machinery**, and a
validator rejects a Senate contest carrying a plan or a House contest
missing one.

### Geometry attaches to plans, not seats

A House seat (TX-30) is a persistent slot; its boundary is a function of the
governing `DistrictPlan`. 2026 features mid-decade redistricting — new
plans in **TX, CA, MO, NC, OH, UT** (legislative, ballot-measure,
commission, and court-ordered; several with `litigation_pending=True`) —
so every House contest carries a mandatory `under_plan_id`, and map features
in those states are flagged `geometry_may_be_superseded` because TIGER may
lag the 2025 plans.

### Specials are term-completing

The FL and OH 2026 Senate specials (Rubio → Moody, Vance → Husted) fill the
**residue of the existing 2023–2029 Class 3 terms**: `target_term_id` is the
same term the vacating senator was elected to, not a new one. A validator
enforces `term_relation == COMPLETING ⇒ trigger == VACANCY` with an attached
`VacancyEvent`.

### Stage graphs, not atomic events

Contest stages form a small DAG: nominating stages (party-scoped primaries,
or party-less CA/WA top-two and AK top-four RCV), optional resolving stages
(TX-style primary runoffs, the GA general runoff — conditionally reachable,
and marked so), and exactly one terminal deciding stage. Louisiana 2026 is
a split system: closed party primaries for U.S. Senate (2024 La. Act 1),
November majority election + December runoff for U.S. House (2026 La. Act 7).

### Honesty over precision

Unverified legal details are marked `UNVERIFIED` in citation descriptions,
and unknown dates are `None` with `TODO` citations. An honest gap beats a
fabricated statute. Most dates and citations were verified against state
election-calendar and statute sources in July 2026.

## Architecture

Python generates and validates the data; TypeScript renders it; **static
files are the contract** between them. No database in v0 — the full dataset
(470 contests + simplified geometries) ships as static JSON/GeoJSON and the
point query runs client-side. Postgres/PostGIS is the known upgrade path.

```
pipeline/            Python (conda env midterm-ontology-2026)
  models.py          the schema — Pydantic v2, validators encode the ontology
  registry.py        derives ALL 2026 contests from class/apportionment tables
  rules_2026.py      50-state primary rules + dates + statutory citations
  geo.py             TIGER/Line download -> simplify -> tag with plan/contest
  export.py          emits web/public/data/*.json + *.geojson (validated)
  ingest/fec.py      FEC API client shape (not wired in v0)
  tests/             pytest acceptance checks
web/                 Next.js (App Router) + TypeScript
  lib/schema.ts      Zod mirror of models.py (z.discriminatedUnion on chamber)
  lib/pointQuery.ts  point-in-polygon over both layers (turf)
  components/        MapLibre map + contest panel
  tests/             Zod round-trip test over the exported files
```

Schema sync is enforced by the data: the pipeline round-trips every exported
blob through the Pydantic models before writing, and the web test suite
parses the same files with Zod.

## Running it

```bash
# 1. Regenerate all data artifacts (downloads TIGER on first run)
conda run -n midterm-ontology-2026 python -m pipeline.export

# 2. Pipeline acceptance tests
conda run -n midterm-ontology-2026 python -m pytest pipeline/tests

# 3. Web app
cd web && npm install && npm run dev    # http://localhost:3000
npm test                                # Zod round-trip checks
```

Click anywhere on the map: the side panel shows the contest stack at that
point — e.g. Minneapolis returns MN-05 plus the MN Class 2 open-seat
contest with its stage timeline and Art. I § 3 grounding; Columbus returns
OH-03 plus the OH SPECIAL labeled as filling the remainder of the 2023–2029
term. Deep-link with `/?lng=-93.265&lat=44.978`.

## v0 scope

In: all 470 congressional contests, stage DAGs, two Senate specials,
mid-decade plans, simplified TIGER geometry, client-side point query.
Out (deliberately): governors/state legislatures/ballot questions,
Postgres/PostGIS, PMTiles, live FEC sync, results/certification tracking,
auth, deployment config.
