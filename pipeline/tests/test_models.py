"""Acceptance checks 4 and 5: ontology validators and derived facts."""

from datetime import date

import pytest
from pydantic import ValidationError

from pipeline.models import (
    AggregationRule,
    Contest,
    ContestStage,
    HouseSeat,
    SenateSeat,
    StageFunction,
    TermRelation,
    Trigger,
    VacancyEvent,
    is_up_in,
    senate_class_up_in,
)
from pipeline.registry import SENATE_CLASSES, build_vacancies


def _stage(stage_id: str, function: StageFunction, **kw) -> ContestStage:
    kw.setdefault("rule", AggregationRule.plurality)
    kw.setdefault("party_scope", "DEM" if function == StageFunction.nominating else None)
    return ContestStage(stage_id=stage_id, function=function, **kw)


def _contest(**overrides) -> Contest:
    base = dict(
        contest_id="contest/test",
        cycle=2026,
        seat=HouseSeat(state="MN", district_number=5),
        target_term_id="term/test",
        trigger=Trigger.calendar,
        term_relation=TermRelation.initiating,
        under_plan_id="mn-cd-2021",
        stages=[_stage("s/general", StageFunction.deciding)],
    )
    base.update(overrides)
    return Contest(**base)


class TestValidators:
    def test_completing_without_vacancy_raises(self):
        with pytest.raises(ValidationError, match="VacancyEvent"):
            _contest(term_relation=TermRelation.completing,
                     trigger=Trigger.vacancy, vacancy=None)

    def test_completing_without_vacancy_trigger_raises(self):
        vac = build_vacancies()[0]
        with pytest.raises(ValidationError, match="trigger=vacancy"):
            _contest(term_relation=TermRelation.completing,
                     trigger=Trigger.calendar, vacancy=vac)

    def test_completing_with_vacancy_ok(self):
        vac = build_vacancies()[0]
        c = _contest(
            seat=SenateSeat(state="FL", senate_class=3),
            under_plan_id=None,
            trigger=Trigger.vacancy,
            term_relation=TermRelation.completing,
            vacancy=vac,
        )
        assert c.is_special

    def test_senate_contest_with_plan_raises(self):
        with pytest.raises(ValidationError, match="Senate contests"):
            _contest(seat=SenateSeat(state="MN", senate_class=2),
                     under_plan_id="mn-cd-2021")

    def test_house_contest_without_plan_raises(self):
        with pytest.raises(ValidationError, match="under_plan_id"):
            _contest(under_plan_id=None)

    def test_zero_deciding_stages_raises(self):
        with pytest.raises(ValidationError, match="exactly one deciding"):
            _contest(stages=[_stage("s/primary", StageFunction.nominating)])

    def test_two_deciding_stages_raises(self):
        with pytest.raises(ValidationError, match="exactly one deciding"):
            _contest(stages=[
                _stage("s/general", StageFunction.deciding),
                _stage("s/general2", StageFunction.deciding),
            ])

    def test_nominating_stage_needs_party_scope_or_top_n(self):
        with pytest.raises(ValidationError, match="party_scope or a top-N"):
            ContestStage(stage_id="s/primary",
                         function=StageFunction.nominating,
                         rule=AggregationRule.plurality,
                         party_scope=None)
        # party-less is fine when the rule itself is top-N
        ContestStage(stage_id="s/primary", function=StageFunction.nominating,
                     rule=AggregationRule.top_two, party_scope=None)

    def test_majority_runoff_defaults_threshold(self):
        s = ContestStage(stage_id="s/general",
                         function=StageFunction.deciding,
                         rule=AggregationRule.majority_runoff)
        assert s.runoff_threshold == 0.5


class TestDerivedFacts:
    def test_senate_class_anchors(self):
        # Class 3 elected 2016 -> up 2022; Class 1 elected 2018 -> up 2024;
        # Class 2 elected 2020 -> up 2026.
        assert senate_class_up_in(2022) == 3
        assert senate_class_up_in(2024) == 1
        assert senate_class_up_in(2026) == 2
        assert senate_class_up_in(2028) == 3

    def test_odd_cycle_raises(self):
        with pytest.raises(ValueError):
            senate_class_up_in(2027)

    def test_house_up_every_even_cycle(self):
        seat = HouseSeat(state="TX", district_number=30)
        assert is_up_in(seat, 2026)
        assert is_up_in(seat, 2024)

    def test_senate_vacancy_makes_seat_up(self):
        vacancies = build_vacancies()
        fl3 = SenateSeat(state="FL", senate_class=3)
        oh3 = SenateSeat(state="OH", senate_class=3)
        ca3 = SenateSeat(state="CA", senate_class=3)
        assert is_up_in(fl3, 2026, vacancies)
        assert is_up_in(oh3, 2026, vacancies)
        assert not is_up_in(ca3, 2026, vacancies)

    def test_exactly_35_senate_seats_up_in_2026(self):
        """Acceptance check 5: 33 Class 2 seats + FL/OH Class 3 vacancies."""
        vacancies = build_vacancies()
        seats = [
            SenateSeat(state=state, senate_class=cls)
            for state, classes in SENATE_CLASSES.items()
            for cls in classes
        ]
        assert len(seats) == 100
        up = [s for s in seats if is_up_in(s, 2026, vacancies)]
        assert len(up) == 35
