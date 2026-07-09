"""Per-state primary rules and 2026 dates, and the ContestStage graph builder.

Honesty policy (from the project brief): dates are filled only where
confident; unknown dates are None and unknown statutes are "TODO". A
citation whose description contains "UNVERIFIED" has not been checked
against the primary source. An honest gap beats a fabricated statute.

Stage semantics:
  * party-primary states get one nominating stage per major party
    (party_scope DEM / REP), advancing to the deciding general;
  * runoff states additionally get per-party resolving stages that are
    only conditionally reachable (see stage.note);
  * CA/WA use a single party-less top-two nominating stage; AK a single
    top-four stage whose general is decided by ranked-choice tabulation;
  * LA is modeled with its majority system (all-comers November election
    counted as the deciding stage, December runoff as a conditionally
    reachable resolving stage) — see the LA note about the 2024 closed-
    primary law;
  * GA's deciding general carries rule=majority_runoff and a resolving
    December general-runoff stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .models import (
    AggregationRule,
    ContestStage,
    LegalCitation,
    StageFunction,
)

GENERAL_2026 = date(2026, 11, 3)  # 2 U.S.C. § 7 (House), § 1 (Senate)

GENERAL_ELECTION_GROUNDING = LegalCitation(
    instrument="2 U.S.C. § 7; 2 U.S.C. § 1",
    description=(
        "Tuesday next after the first Monday in November in even-numbered "
        "years fixed as the federal general election day"
    ),
    url="https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title2-section7",
)


@dataclass(frozen=True)
class StateRules:
    """One state's 2026 primary system for congressional races."""

    primary_type: str  # closed | open | semi_closed | top_two | top_four_rcv | majority_general
    primary_date: Optional[date]
    primary_runoff_date: Optional[date] = None
    primary_runoff_threshold: Optional[float] = None
    general_runoff_date: Optional[date] = None
    general_runoff_threshold: Optional[float] = None
    citation: str = "TODO"
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# The 50-state table.
# ---------------------------------------------------------------------------

RULES_2026: dict[str, StateRules] = {
    "AL": StateRules("open", date(2026, 5, 19), date(2026, 6, 16), 0.5,
                     citation="Ala. Code § 17-13-3 (UNVERIFIED)"),
    "AK": StateRules("top_four_rcv", date(2026, 8, 18),
                     citation="Alaska Stat. § 15.25.010 (UNVERIFIED)",
                     note="Top-four primary; general decided by ranked-choice tabulation"),
    "AZ": StateRules("semi_closed", date(2026, 8, 4),
                     citation="Ariz. Rev. Stat. § 16-201 (UNVERIFIED)"),
    "AR": StateRules("open", date(2026, 3, 3), date(2026, 3, 31), 0.5,
                     citation="Ark. Code § 7-7-203 (UNVERIFIED)"),
    "CA": StateRules("top_two", date(2026, 6, 2),
                     citation="Cal. Const. art. II, § 5; Cal. Elec. Code § 1201",
                     note="Voter-nominated top-two primary; all candidates on one ballot"),
    "CO": StateRules("semi_closed", date(2026, 6, 30),
                     citation="Colo. Rev. Stat. § 1-4-101 (UNVERIFIED)"),
    "CT": StateRules("closed", date(2026, 8, 11),
                     citation="Conn. Gen. Stat. § 9-415 (UNVERIFIED)"),
    "DE": StateRules("closed", date(2026, 9, 8),
                     citation="TODO"),
    "FL": StateRules("closed", date(2026, 8, 18),
                     citation="Fla. Stat. § 100.061"),
    "GA": StateRules("open", date(2026, 5, 19), date(2026, 6, 16), 0.5,
                     general_runoff_date=date(2026, 12, 1),
                     general_runoff_threshold=0.5,
                     citation="O.C.G.A. § 21-2-150; runoffs O.C.G.A. § 21-2-501"),
    "HI": StateRules("open", date(2026, 8, 8),
                     citation="Haw. Rev. Stat. § 12-2 (UNVERIFIED)"),
    "ID": StateRules("closed", date(2026, 5, 19),
                     citation="Idaho Code § 34-601 (UNVERIFIED)"),
    "IL": StateRules("open", date(2026, 3, 17),
                     citation="10 ILCS 5/2A-1.1"),
    "IN": StateRules("open", date(2026, 5, 5),
                     citation="Ind. Code § 3-10-1-3 (UNVERIFIED)"),
    "IA": StateRules("semi_closed", date(2026, 6, 2),
                     citation="Iowa Code § 43.7 (UNVERIFIED)"),
    "KS": StateRules("semi_closed", date(2026, 8, 4),
                     citation="Kan. Stat. § 25-203 (UNVERIFIED)"),
    "KY": StateRules("closed", date(2026, 5, 19),
                     citation="Ky. Rev. Stat. § 118.025 (UNVERIFIED)"),
    "LA": StateRules("majority_general", None,
                     general_runoff_date=date(2026, 12, 5),
                     general_runoff_threshold=0.5,
                     citation="La. R.S. 18:402 (UNVERIFIED)",
                     note=("Modeled as the majority system (November all-comers "
                           "election, December runoff). NOTE: Louisiana's 2024 "
                           "closed-primary law (2024 La. Acts) may move 2026 "
                           "congressional races to closed spring primaries — "
                           "UNVERIFIED, pending confirmation")),
    "ME": StateRules("semi_closed", date(2026, 6, 9),
                     citation="21-A M.R.S. § 339 (UNVERIFIED)",
                     note="Maine tabulates primaries and congressional generals by ranked choice (21-A M.R.S. § 723-A)"),
    "MD": StateRules("closed", date(2026, 6, 30),
                     citation="TODO"),
    "MA": StateRules("semi_closed", None,
                     citation="TODO",
                     note="Primary date set relative to the general; 2026 date unconfirmed"),
    "MI": StateRules("open", date(2026, 8, 4),
                     citation="Mich. Comp. Laws § 168.534 (UNVERIFIED)"),
    "MN": StateRules("open", date(2026, 8, 11),
                     citation="Minn. Stat. § 204D.03"),
    "MS": StateRules("open", date(2026, 6, 2), date(2026, 6, 30), 0.5,
                     citation="Miss. Code § 23-15-191 (UNVERIFIED)"),
    "MO": StateRules("open", date(2026, 8, 4),
                     citation="Mo. Rev. Stat. § 115.121 (UNVERIFIED)"),
    "MT": StateRules("open", date(2026, 6, 2),
                     citation="Mont. Code § 13-1-107 (UNVERIFIED)"),
    "NE": StateRules("semi_closed", date(2026, 5, 12),
                     citation="Neb. Rev. Stat. § 32-401 (UNVERIFIED)"),
    "NV": StateRules("closed", date(2026, 6, 9),
                     citation="Nev. Rev. Stat. § 293.175 (UNVERIFIED)"),
    "NH": StateRules("semi_closed", date(2026, 9, 8),
                     citation="N.H. Rev. Stat. § 653:8 (UNVERIFIED)"),
    "NJ": StateRules("semi_closed", date(2026, 6, 2),
                     citation="N.J. Stat. § 19:2-1 (UNVERIFIED)"),
    "NM": StateRules("closed", date(2026, 6, 2),
                     citation="N.M. Stat. § 1-8-11 (UNVERIFIED)"),
    "NY": StateRules("closed", date(2026, 6, 23),
                     citation="N.Y. Elec. Law § 8-100 (UNVERIFIED)"),
    "NC": StateRules("semi_closed", date(2026, 3, 3), date(2026, 5, 12), 0.30,
                     citation="N.C. Gen. Stat. § 163-1; second primary § 163-111",
                     note="Second primary only on request of the runner-up when leader is under 30%"),
    "ND": StateRules("open", date(2026, 6, 9),
                     citation="N.D. Cent. Code § 16.1-11-01 (UNVERIFIED)"),
    "OH": StateRules("semi_closed", date(2026, 5, 5),
                     citation="Ohio Rev. Code § 3501.01(E)(1)"),
    "OK": StateRules("closed", date(2026, 6, 23), date(2026, 8, 25), 0.5,
                     citation="TODO",
                     note="2026 primary/runoff dates UNVERIFIED"),
    "OR": StateRules("closed", date(2026, 5, 19),
                     citation="Or. Rev. Stat. § 254.056 (UNVERIFIED)"),
    "PA": StateRules("closed", date(2026, 5, 19),
                     citation="25 P.S. § 2753 (UNVERIFIED)"),
    "RI": StateRules("semi_closed", date(2026, 9, 8),
                     citation="TODO"),
    "SC": StateRules("open", date(2026, 6, 9), date(2026, 6, 23), 0.5,
                     citation="S.C. Code § 7-13-40 (UNVERIFIED)"),
    "SD": StateRules("closed", date(2026, 6, 2), date(2026, 8, 11), 0.35,
                     citation="S.D. Codified Laws § 12-2-1 (UNVERIFIED)",
                     note="35% threshold runoff applies to U.S. Senate/House nominations"),
    "TN": StateRules("open", date(2026, 8, 6),
                     citation="Tenn. Code § 2-13-202 (UNVERIFIED)"),
    "TX": StateRules("open", date(2026, 3, 3), date(2026, 5, 26), 0.5,
                     citation="Tex. Elec. Code § 41.007"),
    "UT": StateRules("closed", date(2026, 6, 23),
                     citation="Utah Code § 20A-1-201.5 (UNVERIFIED)"),
    "VT": StateRules("open", date(2026, 8, 11),
                     citation="17 V.S.A. § 2356 (UNVERIFIED)"),
    "VA": StateRules("open", date(2026, 6, 16),
                     citation="Va. Code § 24.2-515 (UNVERIFIED)"),
    "WA": StateRules("top_two", date(2026, 8, 4),
                     citation="RCW 29A.04.311; top-two RCW 29A.52 (UNVERIFIED)",
                     note="All candidates on one ballot; top two advance regardless of party"),
    "WV": StateRules("semi_closed", date(2026, 5, 12),
                     citation="W. Va. Code § 3-5-1 (UNVERIFIED)"),
    "WI": StateRules("open", date(2026, 8, 11),
                     citation="Wis. Stat. § 5.02 (UNVERIFIED)"),
    "WY": StateRules("open", date(2026, 8, 18),
                     citation="Wyo. Stat. § 22-5-211 (UNVERIFIED)"),
}


def scheduling_grounding(state: str) -> LegalCitation:
    """The state-election-code grounding edge for the contest's schedule."""
    rules = RULES_2026[state]
    return LegalCitation(
        instrument=rules.citation,
        description=rules.note or f"{state} 2026 congressional primary scheduling",
    )


def build_stages(state: str, contest_id: str) -> list[ContestStage]:
    """Construct the stage DAG for one contest in `state`.

    Returns nominating stage(s) -> optional resolving runoff(s) ->
    exactly one deciding stage (+ GA/LA conditionally reachable
    post-general resolving runoff).
    """
    rules = RULES_2026[state]
    statutory = scheduling_grounding(state)
    stages: list[ContestStage] = []

    general_id = f"{contest_id}/stage:general"
    general_runoff_id = f"{contest_id}/stage:general-runoff"

    if rules.primary_type == "majority_general":
        # Louisiana majority system: the November all-comers election IS the
        # deciding stage; the December runoff resolves a no-majority result.
        stages.append(ContestStage(
            stage_id=general_id,
            function=StageFunction.deciding,
            rule=AggregationRule.majority_runoff,
            election_date=GENERAL_2026,
            runoff_threshold=rules.general_runoff_threshold,
            advances_to=general_runoff_id,
            statutory_basis=statutory,
            note="All-comers election; majority wins outright",
        ))
        stages.append(ContestStage(
            stage_id=general_runoff_id,
            function=StageFunction.resolving,
            rule=AggregationRule.plurality,
            election_date=rules.general_runoff_date,
            statutory_basis=statutory,
            note="Conditionally reachable: only if no candidate wins a majority in November",
        ))
        return stages

    if rules.primary_type in ("top_two", "top_four_rcv"):
        rule = (AggregationRule.top_two if rules.primary_type == "top_two"
                else AggregationRule.top_four_rcv)
        stages.append(ContestStage(
            stage_id=f"{contest_id}/stage:primary",
            function=StageFunction.nominating,
            rule=rule,
            election_date=rules.primary_date,
            party_scope=None,  # party-less: individuated by the top-N rule
            advances_to=general_id,
            statutory_basis=statutory,
            note=rules.note,
        ))
        stages.append(ContestStage(
            stage_id=general_id,
            function=StageFunction.deciding,
            rule=(AggregationRule.top_four_rcv if rules.primary_type == "top_four_rcv"
                  else AggregationRule.plurality),
            election_date=GENERAL_2026,
            statutory_basis=GENERAL_ELECTION_GROUNDING,
            note=("Decided by ranked-choice tabulation among the top four"
                  if rules.primary_type == "top_four_rcv" else None),
        ))
        return stages

    # Party-scoped primaries (closed / open / semi_closed).
    has_primary_runoff = rules.primary_runoff_threshold is not None
    primary_rule = (AggregationRule.majority_runoff if has_primary_runoff
                    else AggregationRule.plurality)
    for party in ("DEM", "REP"):
        primary_id = f"{contest_id}/stage:primary:{party.lower()}"
        runoff_id = f"{contest_id}/stage:primary-runoff:{party.lower()}"
        stages.append(ContestStage(
            stage_id=primary_id,
            function=StageFunction.nominating,
            rule=primary_rule,
            election_date=rules.primary_date,
            party_scope=party,
            runoff_threshold=rules.primary_runoff_threshold,
            advances_to=runoff_id if has_primary_runoff else general_id,
            statutory_basis=statutory,
            note=f"{rules.primary_type} primary",
        ))
        if has_primary_runoff:
            stages.append(ContestStage(
                stage_id=runoff_id,
                function=StageFunction.resolving,
                rule=AggregationRule.plurality,
                election_date=rules.primary_runoff_date,
                party_scope=party,
                advances_to=general_id,
                statutory_basis=statutory,
                note=("Conditionally reachable: only if no candidate clears "
                      f"{rules.primary_runoff_threshold:.0%} in the primary"),
            ))

    has_general_runoff = rules.general_runoff_threshold is not None
    stages.append(ContestStage(
        stage_id=general_id,
        function=StageFunction.deciding,
        rule=(AggregationRule.majority_runoff if has_general_runoff
              else AggregationRule.plurality),
        election_date=GENERAL_2026,
        runoff_threshold=rules.general_runoff_threshold,
        advances_to=general_runoff_id if has_general_runoff else None,
        statutory_basis=GENERAL_ELECTION_GROUNDING,
    ))
    if has_general_runoff:
        stages.append(ContestStage(
            stage_id=general_runoff_id,
            function=StageFunction.resolving,
            rule=AggregationRule.plurality,
            election_date=rules.general_runoff_date,
            statutory_basis=statutory,
            note=("Conditionally reachable: only if no candidate wins a "
                  "majority in the general election"),
        ))
    return stages
