"""Per-state primary rules and 2026 dates, and the ContestStage graph builder.

Dates and citations were verified against official state election-calendar
and statute sources (July 2026 research pass); remaining uncertainty is
flagged UNVERIFIED in the citation text. An honest gap beats a fabricated
statute.

Stage semantics:
  * party-primary states get one nominating stage per major party
    (party_scope DEM / REP), advancing to the deciding general;
  * runoff states additionally get per-party resolving stages that are
    only conditionally reachable (see stage.note);
  * CA/WA use a single party-less top-two nominating stage; AK a single
    top-four stage whose general is decided by ranked-choice tabulation;
  * LA runs a SPLIT system in 2026: U.S. Senate races moved to closed
    party primaries (2024 La. Act 1, 1st Ex. Sess.), while U.S. House
    races were rescheduled to the November all-comers majority system
    with a December runoff (2026 La. Act 7, after Louisiana v. Callais);
  * GA's deciding general carries rule=majority_runoff and a resolving
    December general-runoff stage (O.C.G.A. § 21-2-501).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .models import (
    AggregationRule,
    Chamber,
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
    # Stages tabulated by ranked choice within a single event (ME) — no
    # separate runoff election exists or can exist.
    rcv: bool = False


# ---------------------------------------------------------------------------
# The 50-state table (U.S. House rules; LA Senate departs — see below).
# ---------------------------------------------------------------------------

RULES_2026: dict[str, StateRules] = {
    "AL": StateRules("open", date(2026, 5, 19), date(2026, 6, 16), 0.5,
                     citation="Ala. Code § 17-13-3",
                     note=("2026 exception not modeled per-district in v0: after "
                           "Louisiana v. Callais (U.S. Apr. 29, 2026) Alabama "
                           "redrew CDs 1/2/6/7 and held special plurality "
                           "primaries in those districts on 2026-08-11")),
    "AK": StateRules("top_four_rcv", date(2026, 8, 18),
                     citation="Alaska Stat. §§ 15.25.010, 15.25.100; RCV tabulation § 15.15.350",
                     note="Top-four primary; general decided by ranked-choice tabulation"),
    "AZ": StateRules("semi_closed", date(2026, 7, 21),
                     citation="Ariz. Rev. Stat. § 16-201 (as amended by H.B. 2022 (2025))",
                     note="2025 law moved the primary from early August to July"),
    "AR": StateRules("open", date(2026, 3, 3), date(2026, 3, 31), 0.5,
                     citation="Ark. Code Ann. § 7-7-203",
                     note=("2026: a Republican Party rule barred registered "
                           "Democrats from the GOP primary, making it "
                           "effectively semi-closed")),
    "CA": StateRules("top_two", date(2026, 6, 2),
                     citation="Cal. Const. art. II, § 5; Cal. Elec. Code §§ 1201, 8002.5, 8141.5",
                     note="Voter-nominated top-two primary; all candidates on one ballot"),
    "CO": StateRules("semi_closed", date(2026, 6, 30),
                     citation="Colo. Rev. Stat. § 1-4-101"),
    "CT": StateRules("closed", date(2026, 8, 11),
                     citation="Conn. Gen. Stat. § 9-423"),
    "DE": StateRules("closed", date(2026, 9, 15),
                     citation="Del. Code Ann. tit. 15, § 3101"),
    "FL": StateRules("closed", date(2026, 8, 18),
                     citation="Fla. Stat. § 100.061"),
    "GA": StateRules("open", date(2026, 5, 19), date(2026, 6, 16), 0.5,
                     general_runoff_date=date(2026, 12, 1),
                     general_runoff_threshold=0.5,
                     citation="O.C.G.A. § 21-2-150; runoffs O.C.G.A. § 21-2-501",
                     note="General runoff on the 28th day after the general (SB 202 (2021))"),
    "HI": StateRules("open", date(2026, 8, 8),
                     citation="Haw. Rev. Stat. § 12-2"),
    "ID": StateRules("closed", date(2026, 5, 19),
                     citation="Idaho Code § 34-601"),
    "IL": StateRules("open", date(2026, 3, 17),
                     citation="10 ILCS 5/2A-1.1"),
    "IN": StateRules("open", date(2026, 5, 5),
                     citation="Ind. Code § 3-10-1-3"),
    "IA": StateRules("closed", date(2026, 6, 2),
                     citation="Iowa Code § 43.7",
                     note="Closed with same-day party-affiliation change"),
    "KS": StateRules("semi_closed", date(2026, 8, 4),
                     citation="Kan. Stat. Ann. § 25-203"),
    "KY": StateRules("closed", date(2026, 5, 19),
                     citation="Ky. Rev. Stat. § 118.025"),
    "LA": StateRules("majority_general", None,
                     general_runoff_date=date(2026, 12, 12),
                     general_runoff_threshold=0.5,
                     citation="La. R.S. 18:402 (as amended); 2026 La. Act 7",
                     note=("U.S. House 2026: November all-comers majority "
                           "election with Dec. 12 runoff — 2026 La. Act 7 "
                           "rescheduled House races back to this system after "
                           "Louisiana v. Callais; U.S. Senate uses closed "
                           "party primaries (2024 La. Act 1, 1st Ex. Sess.)")),
    "ME": StateRules("semi_closed", date(2026, 6, 9),
                     citation="21-A M.R.S. § 339; RCV 21-A M.R.S. § 723-A",
                     note=("Maine tabulates primaries and congressional "
                           "generals by ranked choice (21-A M.R.S. § 723-A)"),
                     rcv=True),
    "MD": StateRules("closed", date(2026, 6, 23),
                     citation="Md. Code, Elec. Law § 8-201 (as amended by 2025 Md. Laws ch. 311)"),
    "MA": StateRules("semi_closed", date(2026, 9, 1),
                     citation="Mass. Gen. Laws ch. 53, § 28"),
    "MI": StateRules("open", date(2026, 8, 4),
                     citation="Mich. Comp. Laws § 168.534"),
    "MN": StateRules("open", date(2026, 8, 11),
                     citation="Minn. Stat. § 204D.03, subd. 1"),
    "MS": StateRules("open", date(2026, 3, 10), date(2026, 4, 7), 0.5,
                     citation="Miss. Code Ann. § 23-15-1031",
                     note="Mississippi moved its congressional primary to March"),
    "MO": StateRules("open", date(2026, 8, 4),
                     citation="Mo. Rev. Stat. § 115.121.2"),
    "MT": StateRules("open", date(2026, 6, 2),
                     citation="Mont. Code Ann. § 13-1-107"),
    "NE": StateRules("semi_closed", date(2026, 5, 12),
                     citation="Neb. Rev. Stat. § 32-401"),
    "NV": StateRules("closed", date(2026, 6, 9),
                     citation="Nev. Rev. Stat. § 293.175"),
    "NH": StateRules("semi_closed", date(2026, 9, 8),
                     citation="N.H. Rev. Stat. Ann. § 653:8"),
    "NJ": StateRules("semi_closed", date(2026, 6, 2),
                     citation="N.J. Rev. Stat. § 19:23-40"),
    "NM": StateRules("semi_closed", date(2026, 6, 2),
                     citation="N.M. Stat. Ann. § 1-8-11"),
    "NY": StateRules("closed", date(2026, 6, 23),
                     citation="N.Y. Elec. Law § 8-100"),
    "NC": StateRules("semi_closed", date(2026, 3, 3), date(2026, 5, 12), 0.30,
                     citation="N.C. Gen. Stat. § 163-1(b); second primary § 163-111",
                     note=("Second primary only on request of the runner-up "
                           "when the leader is under 30%")),
    "ND": StateRules("open", date(2026, 6, 9),
                     citation="N.D. Cent. Code § 16.1-11-01"),
    "OH": StateRules("semi_closed", date(2026, 5, 5),
                     citation="Ohio Rev. Code Ann. § 3501.01(E)(1)"),
    "OK": StateRules("closed", date(2026, 6, 16), date(2026, 8, 25), 0.5,
                     citation="Okla. Stat. tit. 26, § 1-102"),
    "OR": StateRules("closed", date(2026, 5, 19),
                     citation="Or. Rev. Stat. § 254.056"),
    "PA": StateRules("closed", date(2026, 5, 19),
                     citation="25 P.S. § 2753"),
    "RI": StateRules("semi_closed", date(2026, 9, 9),
                     citation="R.I. Gen. Laws § 17-15-1",
                     note="2026 date per the RI Secretary of State election calendar"),
    "SC": StateRules("open", date(2026, 6, 9), date(2026, 6, 23), 0.5,
                     citation="S.C. Code Ann. § 7-13-15"),
    "SD": StateRules("semi_closed", date(2026, 6, 2), date(2026, 7, 28), 0.35,
                     citation="S.D. Codified Laws § 12-2-1",
                     note="35% threshold runoff applies to U.S. Senate/House nominations"),
    "TN": StateRules("open", date(2026, 8, 6),
                     citation="Tenn. Code Ann. §§ 2-13-202, 2-1-104"),
    "TX": StateRules("open", date(2026, 3, 3), date(2026, 5, 26), 0.5,
                     citation="Tex. Elec. Code § 41.007"),
    "UT": StateRules("semi_closed", date(2026, 6, 23),
                     citation="Utah Code § 20A-1-201.5"),
    "VT": StateRules("open", date(2026, 8, 11),
                     citation="17 V.S.A. § 2351"),
    "VA": StateRules("open", date(2026, 8, 4),
                     citation="Va. Code § 24.2-515; 2026 date reset by H.B. 29 (2026)",
                     note="2026 primary moved from June to August 4 by 2026 legislation"),
    "WA": StateRules("top_two", date(2026, 8, 4),
                     citation="Wash. Rev. Code §§ 29A.04.311, 29A.52.112",
                     note="All candidates on one ballot; top two advance regardless of party"),
    "WV": StateRules("semi_closed", date(2026, 5, 12),
                     citation="W. Va. Code § 3-5-1"),
    "WI": StateRules("open", date(2026, 8, 11),
                     citation="Wis. Stat. § 5.02(12s)"),
    "WY": StateRules("closed", date(2026, 8, 18),
                     citation="Wyo. Stat. § 22-2-104"),
}

# Louisiana's 2026 U.S. SENATE races use closed party primaries (2024 La.
# Act 1, 1st Ex. Sess.; supplemented by Act 640 (2024 R.S.)) — a different
# system than its 2026 U.S. House races.
LA_SENATE_RULES = StateRules(
    "closed", date(2026, 5, 16), date(2026, 6, 27), 0.5,
    citation="2024 La. Act 1 (1st Ex. Sess.); La. R.S. 18:402 (as amended)",
    note="Closed party primaries for U.S. Senate beginning 2026",
)


def _rules_for(state: str, chamber: Chamber) -> StateRules:
    if state == "LA" and chamber == Chamber.senate:
        return LA_SENATE_RULES
    return RULES_2026[state]


def scheduling_grounding(state: str, chamber: Chamber = Chamber.house) -> LegalCitation:
    """The state-election-code grounding edge for the contest's schedule."""
    rules = _rules_for(state, chamber)
    return LegalCitation(
        instrument=rules.citation,
        description=rules.note or f"{state} 2026 congressional primary scheduling",
    )


def build_stages(state: str, contest_id: str,
                 chamber: Chamber = Chamber.house) -> list[ContestStage]:
    """Construct the stage DAG for one contest in `state`.

    Returns nominating stage(s) -> optional resolving runoff(s) ->
    exactly one deciding stage (+ GA/LA conditionally reachable
    post-general resolving runoff).
    """
    rules = _rules_for(state, chamber)
    statutory = scheduling_grounding(state, chamber)
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
    if rules.rcv:
        primary_rule = AggregationRule.ranked_choice
    elif has_primary_runoff:
        primary_rule = AggregationRule.majority_runoff
    else:
        primary_rule = AggregationRule.plurality
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
    if rules.rcv:
        general_rule = AggregationRule.ranked_choice
    elif has_general_runoff:
        general_rule = AggregationRule.majority_runoff
    else:
        general_rule = AggregationRule.plurality
    stages.append(ContestStage(
        stage_id=general_id,
        function=StageFunction.deciding,
        rule=general_rule,
        election_date=GENERAL_2026,
        runoff_threshold=rules.general_runoff_threshold,
        advances_to=general_runoff_id if has_general_runoff else None,
        statutory_basis=GENERAL_ELECTION_GROUNDING,
        note=("Tabulated by ranked choice (21-A M.R.S. § 723-A)"
              if rules.rcv else None),
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
