"""Acceptance checks 1–3: the generated 2026 contest set."""

from pipeline.models import SenateSeat, StageFunction, TermRelation
from pipeline.registry import (
    APPORTIONMENT_2020,
    MID_DECADE_STATES,
    build_registry,
)

AT_LARGE_STATES = {"AK", "DE", "ND", "SD", "VT", "WY"}


class TestSenateContests:
    def test_33_regular_contests_all_class_2(self, registry):
        regular = [c for c in registry.senate_contests if not c.is_special]
        assert len(regular) == 33
        assert all(c.seat.senate_class == 2 for c in regular)
        assert all(c.term_relation == TermRelation.initiating for c in regular)

    def test_two_specials_class_3_completing_2023_2029(self, registry):
        specials = [c for c in registry.senate_contests if c.is_special]
        assert len(specials) == 2
        assert {c.seat.state for c in specials} == {"FL", "OH"}
        for c in specials:
            assert c.seat.senate_class == 3
            assert c.term_relation == TermRelation.completing
            assert c.target_term_id.endswith("2023-2029")
            assert c.vacancy is not None

    def test_specials_target_the_existing_term(self, registry):
        terms = {t.term_id: t for t in registry.terms}
        for c in registry.senate_contests:
            if c.is_special:
                term = terms[c.target_term_id]
                assert term.start.year == 2023 and term.end.year == 2029
                # occupied by the appointed placeholder, not vacant
                assert term.occupant_person_id == c.vacancy.appointee_person_id

    def test_senate_contests_have_no_plan(self, registry):
        assert all(c.under_plan_id is None for c in registry.senate_contests)

    def test_class_grounding_is_article_one(self, registry):
        for c in registry.senate_contests:
            assert "art. I, § 3" in c.seat.class_grounding.instrument


class TestHouseContests:
    def test_435_contests_matching_apportionment(self, registry):
        assert len(registry.house_contests) == 435
        per_state: dict[str, int] = {}
        for c in registry.house_contests:
            per_state[c.seat.state] = per_state.get(c.seat.state, 0) + 1
        assert per_state == APPORTIONMENT_2020

    def test_at_large_states_have_single_district_zero(self, registry):
        for state in AT_LARGE_STATES:
            contests = [c for c in registry.house_contests if c.seat.state == state]
            assert len(contests) == 1
            assert contests[0].seat.district_number == 0
            # at-large constituency resolves to the state division
            assert contests[0].seat.division_id.endswith(f"state:{state.lower()}")

    def test_every_house_contest_has_a_plan(self, registry):
        for c in registry.house_contests:
            assert c.under_plan_id is not None
            assert c.under_plan_id in registry.plans

    def test_mid_decade_states_use_2025_plans(self, registry):
        for c in registry.house_contests:
            plan = registry.plans[c.under_plan_id]
            if c.seat.state in MID_DECADE_STATES:
                assert c.under_plan_id == f"{c.seat.state.lower()}-cd-2025"
                assert plan.superseded_plan_id == f"{c.seat.state.lower()}-cd-2021"
                assert plan.effective_from_cycle == 2026
            else:
                assert c.under_plan_id == f"{c.seat.state.lower()}-cd-2021"
                assert plan.superseded_plan_id is None


class TestStageGraphs:
    def test_every_contest_has_exactly_one_deciding_stage(self, registry):
        for c in registry.contests:
            deciders = [s for s in c.stages if s.function == StageFunction.deciding]
            assert len(deciders) == 1, c.contest_id

    def test_top_two_states_have_partyless_nominating(self, registry):
        for c in registry.contests:
            if c.seat.state in ("CA", "WA"):
                nominating = [s for s in c.stages
                              if s.function == StageFunction.nominating]
                assert len(nominating) == 1
                assert nominating[0].party_scope is None
                assert nominating[0].rule.value == "top_two"

    def test_louisiana_split_system(self, registry):
        # 2026 House races: November all-comers majority election, no
        # separate nominating stage; Senate races: closed party primaries
        # (2024 La. Act 1).
        for c in registry.house_contests:
            if c.seat.state == "LA":
                assert not [s for s in c.stages
                            if s.function == StageFunction.nominating]
        la_senate = [c for c in registry.senate_contests if c.seat.state == "LA"]
        assert len(la_senate) == 1
        nominating = [s for s in la_senate[0].stages
                      if s.function == StageFunction.nominating]
        assert {s.party_scope for s in nominating} == {"DEM", "REP"}

    def test_texas_has_conditional_runoff_stages(self, registry):
        tx = [c for c in registry.house_contests if c.seat.state == "TX"][0]
        resolving = [s for s in tx.stages if s.function == StageFunction.resolving]
        assert resolving and all("onditionally reachable" in (s.note or "")
                                 for s in resolving)

    def test_open_seats_derived_not_stored(self, registry):
        from pipeline.models import contest_kind
        by_id = {c.contest_id: c for c in registry.contests}
        mn = by_id["contest/2026/us-senate/mn/class:2"]
        assert contest_kind(mn) == "open"          # Smith retiring
        fl = by_id["contest/2026/us-senate/fl/class:3/special"]
        assert contest_kind(fl) == "special"
        # 'open'/'special'/'regular' appear nowhere as stored fields
        assert "kind" not in mn.model_dump()
