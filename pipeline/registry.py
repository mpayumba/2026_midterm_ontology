"""Generates the complete 2026 congressional contest set.

Nothing here is hand-listed at the contest level: the 33 regular Senate
contests are DERIVED from the 100-seat class table via `is_up_in`, the two
specials from the vacancy events, and the 435 House contests from the
post-2020-census apportionment table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .models import (
    Annotation,
    Candidacy,
    Contest,
    ContestStatus,
    DistrictPlan,
    HouseSeat,
    IncumbencyStatus,
    LegalCitation,
    PlanAuthor,
    SenateSeat,
    SEVENTEENTH_AMENDMENT,
    Term,
    TermRelation,
    Trigger,
    VacancyEvent,
    is_up_in,
    senate_class_up_in,
)
from .rules_2026 import build_stages, scheduling_grounding

CYCLE = 2026

# ---------------------------------------------------------------------------
# The 100-seat Senate class table.
# Source: senate.gov class listings —
#   https://www.senate.gov/senators/Class_I.htm
#   https://www.senate.gov/senators/Class_II.htm
#   https://www.senate.gov/senators/Class_III.htm
# Each state holds exactly two seats in two distinct classes.
# ---------------------------------------------------------------------------

SENATE_CLASSES: dict[str, tuple[int, int]] = {
    "AL": (2, 3), "AK": (2, 3), "AZ": (1, 3), "AR": (2, 3), "CA": (1, 3),
    "CO": (2, 3), "CT": (1, 3), "DE": (1, 2), "FL": (1, 3), "GA": (2, 3),
    "HI": (1, 3), "ID": (2, 3), "IL": (2, 3), "IN": (1, 3), "IA": (2, 3),
    "KS": (2, 3), "KY": (2, 3), "LA": (2, 3), "ME": (1, 2), "MD": (1, 3),
    "MA": (1, 2), "MI": (1, 2), "MN": (1, 2), "MS": (1, 2), "MO": (1, 3),
    "MT": (1, 2), "NE": (1, 2), "NV": (1, 3), "NH": (2, 3), "NJ": (1, 2),
    "NM": (1, 2), "NY": (1, 3), "NC": (2, 3), "ND": (1, 3), "OH": (1, 3),
    "OK": (2, 3), "OR": (2, 3), "PA": (1, 3), "RI": (1, 2), "SC": (2, 3),
    "SD": (2, 3), "TN": (1, 2), "TX": (1, 2), "UT": (1, 3), "VT": (1, 3),
    "VA": (1, 2), "WA": (1, 3), "WV": (1, 2), "WI": (1, 3), "WY": (1, 2),
}

assert len(SENATE_CLASSES) == 50
assert sum(1 for pair in SENATE_CLASSES.values() for c in pair) == 100

# ---------------------------------------------------------------------------
# Post-2020-census apportionment (effective 2022–2030 cycles).
# Source: U.S. Census Bureau, 2020 Census Apportionment Results (April 2021).
# District 0 = at-large.
# ---------------------------------------------------------------------------

APPORTIONMENT_2020: dict[str, int] = {
    "AL": 7, "AK": 1, "AZ": 9, "AR": 4, "CA": 52, "CO": 8, "CT": 5, "DE": 1,
    "FL": 28, "GA": 14, "HI": 2, "ID": 2, "IL": 17, "IN": 9, "IA": 4,
    "KS": 4, "KY": 6, "LA": 6, "ME": 2, "MD": 8, "MA": 9, "MI": 13,
    "MN": 8, "MS": 4, "MO": 8, "MT": 2, "NE": 3, "NV": 4, "NH": 2,
    "NJ": 12, "NM": 3, "NY": 26, "NC": 14, "ND": 1, "OH": 15, "OK": 5,
    "OR": 6, "PA": 17, "RI": 2, "SC": 7, "SD": 1, "TN": 9, "TX": 38,
    "UT": 4, "VT": 1, "VA": 11, "WA": 10, "WV": 2, "WI": 8, "WY": 1,
}

assert sum(APPORTIONMENT_2020.values()) == 435

# ---------------------------------------------------------------------------
# District plans. Geometry belongs to plans, not seats.
# ---------------------------------------------------------------------------

# States whose operative post-2020-census plan was drawn by an independent
# commission or by a court (best-effort; UNVERIFIED details are flagged in
# the citation description).
_COMMISSION_2021 = {"AZ", "CA", "CO", "HI", "ID", "MI", "MT", "NJ", "WA"}
_COURT_2021 = {"CT", "MN", "NH", "PA", "VA", "WI"}

# 2026 features mid-decade redistricting: these states enter the cycle under
# a NEW 2025 plan that supersedes their post-2020-census plan.
MID_DECADE_STATES = {"TX", "CA", "MO", "NC", "OH", "UT"}


def _plan_2021(state: str) -> DistrictPlan:
    if state in _COMMISSION_2021:
        author = PlanAuthor.commission
    elif state in _COURT_2021:
        author = PlanAuthor.court
    else:
        author = PlanAuthor.legislature
    return DistrictPlan(
        plan_id=f"{state.lower()}-cd-2021",
        state=state,
        enacted_by=author,
        effective_from_cycle=2022,
        authorized_by=LegalCitation(
            instrument=f"{state} post-2020-census congressional plan",
            description=(
                "Operative plan entering the 2026 cycle absent mid-decade "
                "action; enacting-authority detail UNVERIFIED for some "
                "states (interim court maps and later re-enactments are "
                "collapsed into this plan id in v0)"
            ),
        ),
        geometry_ref="house_districts.geojson",
    )


def _mid_decade_plans() -> dict[str, DistrictPlan]:
    """The 2025 mid-decade congressional plans. Litigation-heavy: flags and
    UNVERIFIED markers are deliberate."""
    plans = {
        "TX": DistrictPlan(
            plan_id="tx-cd-2025",
            state="TX",
            enacted_by=PlanAuthor.legislature,
            effective_from_cycle=2026,
            authorized_by=LegalCitation(
                instrument="Tex. 89th Leg., 2025 special session congressional plan (H.B. 4)",
                description=(
                    "Mid-decade plan enacted August 2025; a three-judge "
                    "federal panel blocked it in late 2025 but the U.S. "
                    "Supreme Court stayed that ruling, leaving the plan in "
                    "use for 2026 (UNVERIFIED details)"
                ),
            ),
            superseded_plan_id="tx-cd-2021",
            geometry_ref="house_districts.geojson",
            litigation_pending=True,
        ),
        "CA": DistrictPlan(
            plan_id="ca-cd-2025",
            state="CA",
            enacted_by=PlanAuthor.legislature,
            effective_from_cycle=2026,
            authorized_by=LegalCitation(
                instrument="Cal. Proposition 50 (Nov. 2025)",
                description=(
                    "Legislatively referred ballot measure (Election "
                    "Rigging Response Act) adopting a legislature-drawn "
                    "map in place of the 2021 commission plan for "
                    "2026–2030; approved by voters Nov. 2025"
                ),
            ),
            superseded_plan_id="ca-cd-2021",
            geometry_ref="house_districts.geojson",
            litigation_pending=True,
        ),
        "MO": DistrictPlan(
            plan_id="mo-cd-2025",
            state="MO",
            enacted_by=PlanAuthor.legislature,
            effective_from_cycle=2026,
            authorized_by=LegalCitation(
                instrument="Mo. 2025 special session congressional plan (H.B. 1)",
                description=(
                    "Mid-decade plan enacted September 2025; subject to "
                    "referendum-petition and court challenges (UNVERIFIED "
                    "details)"
                ),
            ),
            superseded_plan_id="mo-cd-2021",
            geometry_ref="house_districts.geojson",
            litigation_pending=True,
        ),
        "NC": DistrictPlan(
            plan_id="nc-cd-2025",
            state="NC",
            enacted_by=PlanAuthor.legislature,
            effective_from_cycle=2026,
            authorized_by=LegalCitation(
                instrument="N.C. Gen. Assemb., October 2025 congressional plan",
                description=(
                    "Mid-decade plan; supersedes the prior post-2020-census "
                    "lineage (2021/2023 maps collapsed into nc-cd-2021 in "
                    "v0); challenged in federal court (UNVERIFIED details)"
                ),
            ),
            superseded_plan_id="nc-cd-2021",
            geometry_ref="house_districts.geojson",
            litigation_pending=True,
        ),
        "OH": DistrictPlan(
            plan_id="oh-cd-2025",
            state="OH",
            enacted_by=PlanAuthor.legislature,
            effective_from_cycle=2026,
            authorized_by=LegalCitation(
                instrument="Ohio Const. art. XIX; 2025 congressional plan",
                description=(
                    "Redraw required because the 2021 plan passed without "
                    "bipartisan support and expired after four years; 2025 "
                    "plan enacted with bipartisan support (UNVERIFIED "
                    "details)"
                ),
            ),
            superseded_plan_id="oh-cd-2021",
            geometry_ref="house_districts.geojson",
            litigation_pending=False,
        ),
        "UT": DistrictPlan(
            plan_id="ut-cd-2025",
            state="UT",
            enacted_by=PlanAuthor.court,
            effective_from_cycle=2026,
            authorized_by=LegalCitation(
                instrument="League of Women Voters v. Utah Legislature (Utah 3d Dist. Ct. 2025)",
                description=(
                    "Court-ordered remedial map after the Utah Supreme "
                    "Court's Proposition 4 ruling invalidated the 2021 "
                    "plan; appeal exposure remains (UNVERIFIED details)"
                ),
            ),
            superseded_plan_id="ut-cd-2021",
            geometry_ref="house_districts.geojson",
            litigation_pending=True,
        ),
    }
    assert set(plans) == MID_DECADE_STATES
    return plans


def build_plans() -> dict[str, DistrictPlan]:
    """All district plans, keyed by plan_id. Mid-decade states carry both
    their superseded 2021 plan and the operative 2025 plan."""
    plans = {p.plan_id: p for p in (_plan_2021(st) for st in APPORTIONMENT_2020)}
    for plan in _mid_decade_plans().values():
        plans[plan.plan_id] = plan
    return plans


def governing_plan_id(state: str) -> str:
    """The plan governing `state`'s House contests in the 2026 cycle."""
    if state in MID_DECADE_STATES:
        return f"{state.lower()}-cd-2025"
    return f"{state.lower()}-cd-2021"


# ---------------------------------------------------------------------------
# Vacancy events → the two Senate specials. Term-completing: the winner
# serves the residue of the SAME Class 3 term (2023–2029) the vacating
# senator was elected to.
# ---------------------------------------------------------------------------


def build_vacancies() -> list[VacancyEvent]:
    fl_seat = SenateSeat(state="FL", senate_class=3)
    oh_seat = SenateSeat(state="OH", senate_class=3)
    return [
        VacancyEvent(
            seat_id=fl_seat.seat_id,
            vacated_by_person_id="person/marco-rubio",
            reason="Resigned January 2025 to serve as U.S. Secretary of State",
            vacancy_date=date(2025, 1, 20),
            appointee_person_id="person/ashley-moody",
            appointed_by="Gov. Ron DeSantis (R-FL)",
            appointment_grounding=LegalCitation(
                instrument=f"{SEVENTEENTH_AMENDMENT.instrument}; Fla. Stat. § 100.161",
                description=(
                    "17th Amendment temporary-appointment power as directed "
                    "by Florida's Senate-vacancy statute"
                ),
            ),
        ),
        VacancyEvent(
            seat_id=oh_seat.seat_id,
            vacated_by_person_id="person/jd-vance",
            reason="Resigned January 2025 to serve as Vice President of the United States",
            vacancy_date=date(2025, 1, 10),
            appointee_person_id="person/jon-husted",
            appointed_by="Gov. Mike DeWine (R-OH)",
            appointment_grounding=LegalCitation(
                instrument=f"{SEVENTEENTH_AMENDMENT.instrument}; Ohio Rev. Code § 3.02 (UNVERIFIED)",
                description=(
                    "17th Amendment temporary-appointment power as directed "
                    "by Ohio's vacancy statute"
                ),
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Seed candidacies (v0 stubs — see pipeline/ingest/fec.py for the live path)
# ---------------------------------------------------------------------------

_SEED_CANDIDACIES: dict[str, list[Candidacy]] = {
    "contest/2026/us-senate/mn/class:2": [
        Candidacy(person_id="person/tina-smith", person_name="Tina Smith",
                  party="DFL", incumbency=IncumbencyStatus.retiring),
        Candidacy(person_id="person/peggy-flanagan", person_name="Peggy Flanagan",
                  party="DFL", incumbency=IncumbencyStatus.not_incumbent),
    ],
    "contest/2026/us-senate/nc/class:2": [
        Candidacy(person_id="person/thom-tillis", person_name="Thom Tillis",
                  party="REP", incumbency=IncumbencyStatus.retiring),
        Candidacy(person_id="person/roy-cooper", person_name="Roy Cooper",
                  party="DEM", incumbency=IncumbencyStatus.not_incumbent),
        Candidacy(person_id="person/michael-whatley", person_name="Michael Whatley",
                  party="REP", incumbency=IncumbencyStatus.not_incumbent),
    ],
    "contest/2026/us-senate/fl/class:3/special": [
        Candidacy(person_id="person/ashley-moody", person_name="Ashley Moody",
                  party="REP", incumbency=IncumbencyStatus.appointed_placeholder),
    ],
    "contest/2026/us-senate/oh/class:3/special": [
        Candidacy(person_id="person/jon-husted", person_name="Jon Husted",
                  party="REP", incumbency=IncumbencyStatus.appointed_placeholder),
        Candidacy(person_id="person/sherrod-brown", person_name="Sherrod Brown",
                  party="DEM", incumbency=IncumbencyStatus.not_incumbent),
    ],
}

# Epistemic layer demo: ratings are Annotations ABOUT contests (source +
# timestamp), never fields on them.
_SEED_ANNOTATIONS: dict[str, list[Annotation]] = {
    "contest/2026/us-senate/nc/class:2": [
        Annotation(source="Cook Political Report", kind="rating",
                   as_of=datetime(2025, 7, 31), value="Toss Up"),
    ],
    "contest/2026/us-senate/oh/class:3/special": [
        Annotation(source="Cook Political Report", kind="rating",
                   as_of=datetime(2025, 8, 15), value="Lean Republican"),
    ],
}


# ---------------------------------------------------------------------------
# Contest generation
# ---------------------------------------------------------------------------


def _administered_by(state: str) -> str:
    return f"ocd-division/country:us/state:{state.lower()}"


def build_senate_contests(vacancies: list[VacancyEvent]) -> list[Contest]:
    """Derive the Senate contest set: every seat where `is_up_in` holds.
    Regular (calendar) contests initiate the next term; vacancy contests
    complete the existing one."""
    contests: list[Contest] = []
    regular_class = senate_class_up_in(CYCLE)
    vacancy_by_seat = {v.seat_id: v for v in vacancies}

    for state, classes in sorted(SENATE_CLASSES.items()):
        for senate_class in classes:
            seat = SenateSeat(state=state, senate_class=senate_class)  # type: ignore[arg-type]
            if not is_up_in(seat, CYCLE, vacancies):
                continue
            if senate_class == regular_class:
                contest_id = f"contest/2026/us-senate/{state.lower()}/class:{senate_class}"
                contests.append(Contest(
                    contest_id=contest_id,
                    cycle=CYCLE,
                    seat=seat,
                    target_term_id=f"term/us-senate/{state.lower()}/class:{senate_class}/2027-2033",
                    trigger=Trigger.calendar,
                    term_relation=TermRelation.initiating,
                    stages=build_stages(state, contest_id),
                    candidacies=_SEED_CANDIDACIES.get(contest_id, []),
                    administered_by=_administered_by(state),
                    scheduling_grounding=scheduling_grounding(state),
                    annotations=_SEED_ANNOTATIONS.get(contest_id, []),
                ))
            else:
                vacancy = vacancy_by_seat[seat.seat_id]
                contest_id = f"contest/2026/us-senate/{state.lower()}/class:{senate_class}/special"
                contests.append(Contest(
                    contest_id=contest_id,
                    cycle=CYCLE,
                    seat=seat,
                    # Term-completing: the SAME term the vacating senator won.
                    target_term_id=f"term/us-senate/{state.lower()}/class:{senate_class}/2023-2029",
                    trigger=Trigger.vacancy,
                    term_relation=TermRelation.completing,
                    vacancy=vacancy,
                    stages=build_stages(state, contest_id),
                    candidacies=_SEED_CANDIDACIES.get(contest_id, []),
                    administered_by=_administered_by(state),
                    scheduling_grounding=scheduling_grounding(state),
                    annotations=_SEED_ANNOTATIONS.get(contest_id, []),
                ))
    return contests


def build_house_contests() -> list[Contest]:
    contests: list[Contest] = []
    for state, n_seats in sorted(APPORTIONMENT_2020.items()):
        districts = [0] if n_seats == 1 else list(range(1, n_seats + 1))
        for d in districts:
            seat = HouseSeat(state=state, district_number=d)
            contest_id = f"contest/2026/us-house/{state.lower()}/district:{d}"
            contests.append(Contest(
                contest_id=contest_id,
                cycle=CYCLE,
                seat=seat,
                target_term_id=f"term/us-house/{state.lower()}/district:{d}/2027-2029",
                trigger=Trigger.calendar,
                term_relation=TermRelation.initiating,
                under_plan_id=governing_plan_id(state),
                stages=build_stages(state, contest_id),
                candidacies=_SEED_CANDIDACIES.get(contest_id, []),
                administered_by=_administered_by(state),
                scheduling_grounding=scheduling_grounding(state),
                annotations=_SEED_ANNOTATIONS.get(contest_id, []),
            ))
    return contests


def build_terms(contests: list[Contest], vacancies: list[VacancyEvent]) -> list[Term]:
    """Target terms for every contest. Completing contests target the
    existing term (occupied by the appointed placeholder); initiating
    contests target the next one."""
    appointee_by_seat = {v.seat_id: v.appointee_person_id for v in vacancies}
    terms: dict[str, Term] = {}
    for c in contests:
        if c.term_relation == TermRelation.completing:
            start, end = date(2023, 1, 3), date(2029, 1, 3)
            occupant = appointee_by_seat.get(c.seat.seat_id)
        elif c.seat.chamber == "senate":
            start, end = date(2027, 1, 3), date(2033, 1, 3)
            occupant = None
        else:
            start, end = date(2027, 1, 3), date(2029, 1, 3)
            occupant = None
        terms[c.target_term_id] = Term(
            term_id=c.target_term_id,
            seat_id=c.seat.seat_id,
            start=start,
            end=end,
            occupant_person_id=occupant,
        )
    return list(terms.values())


@dataclass
class Registry:
    contests: list[Contest]
    plans: dict[str, DistrictPlan]
    terms: list[Term]
    vacancies: list[VacancyEvent]

    @property
    def senate_contests(self) -> list[Contest]:
        return [c for c in self.contests if c.seat.chamber == "senate"]

    @property
    def house_contests(self) -> list[Contest]:
        return [c for c in self.contests if c.seat.chamber == "house"]


def build_registry() -> Registry:
    vacancies = build_vacancies()
    contests = build_senate_contests(vacancies) + build_house_contests()
    return Registry(
        contests=contests,
        plans=build_plans(),
        terms=build_terms(contests, vacancies),
        vacancies=vacancies,
    )
