"""Ontology schema for the 2026 U.S. midterm congressional cycle.

Three layers, kept typed apart:

* **Structural (de jure)** — seats, district plans, terms, legal citations.
  Grounded in legal instruments via `LegalCitation` edges.
* **Event (de facto)** — contests, stages, candidacies, vacancies: the 2026
  cycle as time-indexed assertions over the structural layer.
* **Epistemic** — `Annotation`s: ratings/forecasts as credences ABOUT
  contests (source + timestamp), never fields on them.

The central entity is the **Contest**: the process of filling one Term of one
Seat. What voters call "an election" is three distinct things — the
administered Election (a state-run event on a date), the Contest, and the
ContestStage (the contest's appearance in one administered election).

Derived facts (is this seat up? how many seats flip a chamber?) are functions
at the bottom of this module — never stored fields. If it is a theorem of the
ontology, it is a function in the code.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any, Iterable, Literal, Optional, Union

from pydantic import BaseModel, Field, computed_field, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Chamber(str, Enum):
    senate = "senate"
    house = "house"


class Trigger(str, Enum):
    """Why the contest exists: the calendar, or a vacancy event."""

    calendar = "calendar"
    vacancy = "vacancy"


class TermRelation(str, Enum):
    """Relation of the contest to its target term.

    initiating — the contest creates/fills a brand-new term.
    completing — the contest fills the residue of an EXISTING term
                 (Senate specials: the winner serves out the term the
                 vacating senator was elected to).
    """

    initiating = "initiating"
    completing = "completing"


class StageFunction(str, Enum):
    nominating = "nominating"  # primaries — party-scoped or top-N
    resolving = "resolving"    # runoffs — conditionally reachable
    deciding = "deciding"      # the terminal stage that seats a winner


class AggregationRule(str, Enum):
    plurality = "plurality"
    majority_runoff = "majority_runoff"
    top_two = "top_two"
    top_four_rcv = "top_four_rcv"


class IncumbencyStatus(str, Enum):
    running = "running"
    retiring = "retiring"
    lost_nomination = "lost_nomination"
    appointed_placeholder = "appointed_placeholder"
    not_incumbent = "not_incumbent"


class ContestStatus(str, Enum):
    """Lifecycle. PROJECTED is a media call; CERTIFIED is the legal
    truth-maker. They are distinct states, never conflated."""

    scheduled = "scheduled"
    ballot_set = "ballot_set"
    voting = "voting"
    counting = "counting"
    projected = "projected"
    certified = "certified"
    contested = "contested"


class PlanAuthor(str, Enum):
    legislature = "legislature"
    commission = "commission"
    court = "court"


# ---------------------------------------------------------------------------
# Structural layer (de jure)
# ---------------------------------------------------------------------------


class LegalCitation(BaseModel):
    """A grounding edge: the legal instrument that authorizes a structural
    fact. Descriptions marked UNVERIFIED flag details not yet confirmed
    against the primary source — an honest gap beats invented precision."""

    instrument: str
    description: Optional[str] = None
    url: Optional[str] = None


ART_I_S3_CL2 = LegalCitation(
    instrument="U.S. Const. art. I, § 3, cl. 2",
    description=(
        "Division of senators into three classes so that one-third of "
        "seats face election every second year"
    ),
    url="https://constitution.congress.gov/browse/article-1/section-3/",
)

SEVENTEENTH_AMENDMENT = LegalCitation(
    instrument="U.S. Const. amend. XVII",
    description=(
        "Direct election of senators; authorizes governors to make "
        "temporary appointments until the people fill the vacancy by "
        "election, as the state legislature may direct"
    ),
    url="https://constitution.congress.gov/browse/amendment-17/",
)


class DistrictPlan(BaseModel):
    """A legally enacted congressional district map. Geometry attaches to
    plans, NOT to seats: a House seat is a persistent slot whose boundary is
    a function of the governing plan."""

    plan_id: str
    state: str = Field(pattern=r"^[A-Z]{2}$")
    enacted_by: PlanAuthor
    effective_from_cycle: int
    authorized_by: LegalCitation
    superseded_plan_id: Optional[str] = None
    geometry_ref: Optional[str] = None
    litigation_pending: bool = False


class SenateSeat(BaseModel):
    """Individuated by (state, class). Its constituency is the state
    division directly — a Senate seat has NO district or plan machinery."""

    chamber: Literal["senate"] = "senate"
    state: str = Field(pattern=r"^[A-Z]{2}$")
    senate_class: Literal[1, 2, 3]
    class_grounding: LegalCitation = Field(
        default_factory=lambda: ART_I_S3_CL2.model_copy()
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def seat_id(self) -> str:
        return f"ocd-seat/us-senate/{self.state.lower()}/class:{self.senate_class}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def division_id(self) -> str:
        return f"ocd-division/country:us/state:{self.state.lower()}"


class HouseSeat(BaseModel):
    """Individuated by (state, district_number). district_number 0 means
    at-large; its constituency then resolves to the state division."""

    chamber: Literal["house"] = "house"
    state: str = Field(pattern=r"^[A-Z]{2}$")
    district_number: int = Field(ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def seat_id(self) -> str:
        return f"ocd-seat/us-house/{self.state.lower()}/district:{self.district_number}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def division_id(self) -> str:
        state_div = f"ocd-division/country:us/state:{self.state.lower()}"
        if self.district_number == 0:
            return state_div
        return f"{state_div}/cd:{self.district_number}"


Seat = Annotated[Union[SenateSeat, HouseSeat], Field(discriminator="chamber")]


class Term(BaseModel):
    """One term of one seat: the thing a contest targets."""

    term_id: str
    seat_id: str
    start: date
    end: date
    occupant_person_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Event layer (de facto)
# ---------------------------------------------------------------------------


class VacancyEvent(BaseModel):
    seat_id: str
    vacated_by_person_id: str
    reason: str
    vacancy_date: date
    appointee_person_id: Optional[str] = None
    appointed_by: Optional[str] = None
    appointment_grounding: Optional[LegalCitation] = None


class Candidacy(BaseModel):
    """A person's candidacy in one contest. A record with
    incumbency=retiring encodes the incumbent's disposition (making the
    seat derivably open) rather than an actual filing."""

    person_id: str
    person_name: str
    party: Optional[str] = None
    incumbency: IncumbencyStatus
    filing_date: Optional[date] = None
    stage_results: dict[str, Any] = Field(default_factory=dict)


class ContestStage(BaseModel):
    """A contest's appearance in one administered election. Stages form a
    small DAG via `advances_to`; resolving stages (runoffs) are only
    conditionally reachable — see `note`."""

    stage_id: str
    function: StageFunction
    rule: AggregationRule
    election_date: Optional[date] = None
    party_scope: Optional[str] = None
    runoff_threshold: Optional[float] = None
    advances_to: Optional[str] = None
    statutory_basis: Optional[LegalCitation] = None
    note: Optional[str] = None

    @model_validator(mode="after")
    def _check_stage(self) -> "ContestStage":
        if self.rule == AggregationRule.majority_runoff and self.runoff_threshold is None:
            self.runoff_threshold = 0.5
        if self.function == StageFunction.nominating:
            has_top_n_rule = self.rule in (
                AggregationRule.top_two,
                AggregationRule.top_four_rcv,
            )
            if self.party_scope is None and not has_top_n_rule:
                raise ValueError(
                    f"nominating stage {self.stage_id!r} must have a "
                    "party_scope or a top-N rule (top_two / top_four_rcv)"
                )
        return self


# ---------------------------------------------------------------------------
# Epistemic layer
# ---------------------------------------------------------------------------


class Annotation(BaseModel):
    """A credence ABOUT a contest — rating, forecast, projection — with its
    source and timestamp. Epistemic, never a field on the factual layers."""

    source: str
    as_of: datetime
    kind: str
    value: Any


# ---------------------------------------------------------------------------
# The central entity
# ---------------------------------------------------------------------------


class Contest(BaseModel):
    """The process of filling one Term of one Seat."""

    contest_id: str
    cycle: int
    seat: Seat
    target_term_id: str
    trigger: Trigger
    term_relation: TermRelation
    vacancy: Optional[VacancyEvent] = None
    under_plan_id: Optional[str] = None
    stages: list[ContestStage] = Field(default_factory=list)
    candidacies: list[Candidacy] = Field(default_factory=list)
    administered_by: Optional[str] = None
    status: ContestStatus = ContestStatus.scheduled
    scheduling_grounding: Optional[LegalCitation] = None
    annotations: list[Annotation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_ontology(self) -> "Contest":
        # Specials are term-completing: completing requires a vacancy
        # trigger AND the attached VacancyEvent that explains it.
        if self.term_relation == TermRelation.completing:
            if self.trigger != Trigger.vacancy:
                raise ValueError(
                    f"{self.contest_id}: term_relation=completing requires "
                    "trigger=vacancy"
                )
            if self.vacancy is None:
                raise ValueError(
                    f"{self.contest_id}: term_relation=completing requires "
                    "an attached VacancyEvent"
                )
        # A Senate contest's constituency is the state division directly —
        # it has no plan machinery. A House seat's boundary is a function
        # of the governing plan, so the plan reference is mandatory.
        if isinstance(self.seat, SenateSeat) and self.under_plan_id is not None:
            raise ValueError(
                f"{self.contest_id}: Senate contests must not reference a "
                "DistrictPlan (constituency is the state division)"
            )
        if isinstance(self.seat, HouseSeat) and self.under_plan_id is None:
            raise ValueError(
                f"{self.contest_id}: House contests must reference the "
                "governing DistrictPlan via under_plan_id"
            )
        # The stage DAG has exactly one terminal deciding stage.
        if self.stages:
            deciders = [s for s in self.stages if s.function == StageFunction.deciding]
            if len(deciders) != 1:
                raise ValueError(
                    f"{self.contest_id}: stage graph must contain exactly "
                    f"one deciding stage, found {len(deciders)}"
                )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def general_date(self) -> Optional[date]:
        for s in self.stages:
            if s.function == StageFunction.deciding:
                return s.election_date
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_special(self) -> bool:
        return self.trigger == Trigger.vacancy


# ---------------------------------------------------------------------------
# Derived facts — functions, never stored fields
# ---------------------------------------------------------------------------

# Anchor: Class 2 senators were elected in 2020 (2020 % 6 == 4), so Class 2
# is up again in 2026. Class 3 was up in 2022 (mod 0), Class 1 in 2024
# (mod 2). Grounded in U.S. Const. art. I, § 3, cl. 2.
# NB: the project brief's inline mapping ("2→2, 4→1") contradicts its own
# anchor ("Class 2 up in 2020 ⇒ 2026"); the anchor is what matches reality
# and the acceptance checks, so it wins.
_CLASS_UP_BY_CYCLE_MOD: dict[int, Literal[1, 2, 3]] = {0: 3, 2: 1, 4: 2}


def senate_class_up_in(cycle: int) -> Literal[1, 2, 3]:
    """Which Senate class faces regular (calendar-triggered) election in
    `cycle`. Raises on odd years — there is no regular federal cycle."""
    if cycle % 2 != 0:
        raise ValueError(f"{cycle} is not a federal election cycle")
    return _CLASS_UP_BY_CYCLE_MOD[cycle % 6]


def is_up_in(
    seat: Union[SenateSeat, HouseSeat],
    cycle: int,
    vacancies: Iterable[VacancyEvent] = (),
) -> bool:
    """Is this seat on the ballot in `cycle`? Computed from Senate class
    staggering + vacancy events — never stored."""
    if isinstance(seat, HouseSeat):
        return cycle % 2 == 0
    if seat.senate_class == senate_class_up_in(cycle):
        return True
    return any(v.seat_id == seat.seat_id for v in vacancies)


def is_open_seat(contest: Contest) -> bool:
    """No incumbent (elected or appointed) is seeking the seat. Unknown
    when no candidacies are recorded — defaults to False."""
    if not contest.candidacies:
        return False
    incumbent_seeking = any(
        c.incumbency
        in (IncumbencyStatus.running, IncumbencyStatus.appointed_placeholder)
        for c in contest.candidacies
    )
    return not incumbent_seeking


def contest_kind(contest: Contest) -> str:
    """Projection for display: special > open > regular. Derived, exported
    as a convenience property on map features — never stored on Contest."""
    if contest.is_special:
        return "special"
    if is_open_seat(contest):
        return "open"
    return "regular"


def net_seats_to_flip(
    seats_held: dict[str, int], majority_of: int, party: str
) -> int:
    """Majority arithmetic from the seat graph + occupancy: how many net
    seats `party` must gain for a bare majority of a chamber of size
    `majority_of`. A theorem of the ontology, so a function."""
    needed = majority_of // 2 + 1
    return max(0, needed - seats_held.get(party, 0))
