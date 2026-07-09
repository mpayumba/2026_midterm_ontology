"""Acceptance check 7 (+ export integrity): point queries over the exported
layers. Requires the artifacts from `python -m pipeline.export`."""

import json
from pathlib import Path

import pytest
from shapely.geometry import Point, shape

from pipeline.export import WEB_DATA_DIR

MINNEAPOLIS = Point(-93.2650, 44.9778)   # downtown Minneapolis
COLUMBUS = Point(-82.9988, 39.9612)      # downtown Columbus


def _load(name: str):
    path = WEB_DATA_DIR / name
    if not path.exists():
        pytest.fail(
            f"{path} missing — run `python -m pipeline.export` before pytest"
        )
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def house_fc():
    return _load("house_districts.geojson")


@pytest.fixture(scope="module")
def states_fc():
    return _load("states_senate.geojson")


@pytest.fixture(scope="module")
def contests():
    return _load("contests.json")


def _features_at(fc: dict, point: Point) -> list[dict]:
    return [f for f in fc["features"] if shape(f["geometry"]).contains(point)]


class TestExportIntegrity:
    def test_house_layer_has_435_features(self, house_fc):
        assert len(house_fc["features"]) == 435

    def test_size_budget(self):
        total = sum((WEB_DATA_DIR / n).stat().st_size
                    for n in ("house_districts.geojson", "states_senate.geojson"))
        assert total <= 5_000_000, f"geometry exceeds 5 MB budget: {total}"

    def test_every_feature_contest_exists(self, house_fc, contests):
        contest_ids = {c["contest_id"] for c in contests}
        for f in house_fc["features"]:
            assert f["properties"]["contest_id"] in contest_ids

    def test_mid_decade_features_flagged(self, house_fc):
        from pipeline.registry import MID_DECADE_STATES
        for f in house_fc["features"]:
            props = f["properties"]
            assert props["geometry_may_be_superseded"] == (
                props["state"] in MID_DECADE_STATES
            )
            if props["state"] in MID_DECADE_STATES:
                assert props["plan_id"].endswith("-cd-2025")


class TestPointQuery:
    def test_minneapolis_house(self, house_fc):
        """Acceptance check 7: exactly one House contest — MN-05."""
        hits = _features_at(house_fc, MINNEAPOLIS)
        assert len(hits) == 1
        props = hits[0]["properties"]
        assert props["state"] == "MN"
        assert props["district_number"] == 5
        assert props["seat_id"] == "ocd-seat/us-house/mn/district:5"

    def test_minneapolis_senate(self, states_fc):
        """...and exactly one Senate contest — the MN Class 2 open seat."""
        hits = _features_at(states_fc, MINNEAPOLIS)
        assert len(hits) == 1
        props = hits[0]["properties"]
        assert props["state"] == "MN"
        assert props["senate_contest_ids"] == ["contest/2026/us-senate/mn/class:2"]
        assert props["senate_kind"] == "open"

    def test_columbus_house_and_special(self, house_fc, states_fc, contests):
        """Definition-of-done click: OH-03 + the OH Class 3 SPECIAL."""
        house_hits = _features_at(house_fc, COLUMBUS)
        assert len(house_hits) == 1
        assert house_hits[0]["properties"]["seat_id"] == "ocd-seat/us-house/oh/district:3"

        state_hits = _features_at(states_fc, COLUMBUS)
        assert len(state_hits) == 1
        ids = state_hits[0]["properties"]["senate_contest_ids"]
        assert ids == ["contest/2026/us-senate/oh/class:3/special"]

        by_id = {c["contest_id"]: c for c in contests}
        special = by_id[ids[0]]
        assert special["is_special"] is True
        assert special["term_relation"] == "completing"
        assert special["target_term_id"].endswith("2023-2029")
