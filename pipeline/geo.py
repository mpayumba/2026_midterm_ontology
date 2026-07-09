"""Geometry pipeline: TIGER/Line download → simplify → tag with the ontology.

District geometry attaches to PLANS, not seats: each exported feature
carries the plan_id that governs it. In mid-decade states (TX, CA, MO, NC,
OH, UT) TIGER may lag the 2025 plans, so those features are flagged
`geometry_may_be_superseded=true` rather than pretending currency.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .models import contest_kind
from .registry import MID_DECADE_STATES, Registry, governing_plan_id

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Latest available TIGER/Line vintage. Since TIGER2024 the CD product is
# published per state (tl_{year}_{statefps}_cd119.zip), not as one national
# file; the STATE product is still national.
CD_URL_TEMPLATE = "https://www2.census.gov/geo/tiger/TIGER2025/CD/tl_2025_{fips}_cd119.zip"
STATE_URLS = [
    "https://www2.census.gov/geo/tiger/TIGER2025/STATE/tl_2025_us_state.zip",
    "https://www2.census.gov/geo/tiger/TIGER2024/STATE/tl_2024_us_state.zip",
]

STATE_FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "12": "FL", "13": "GA", "15": "HI", "16": "ID",
    "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA",
    "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ",
    "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK",
    "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN",
    "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY",
}


def _download(url: str, raw_dir: Path = RAW_DIR) -> Path:
    """Download one file into data/raw/, skipping when already present."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / url.rsplit("/", 1)[-1]
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with requests.get(url, stream=True, timeout=(30, 300)) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    return dest


def _download_first_available(urls: list[str], raw_dir: Path = RAW_DIR) -> Path:
    """Download the newest available file from `urls`."""
    last_error: Exception | None = None
    for url in urls:
        try:
            return _download(url, raw_dir)
        except Exception as e:  # try the next vintage
            last_error = e
    raise RuntimeError(f"could not download any of {urls}: {last_error}")


def _download_cd_shapefiles(raw_dir: Path = RAW_DIR) -> list[Path]:
    """Fetch the 50 per-state CD119 shapefiles (threaded; skip existing)."""
    urls = [CD_URL_TEMPLATE.format(fips=fips) for fips in sorted(STATE_FIPS)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda u: _download(u, raw_dir), urls))


def _round_coords(obj, ndigits: int = 5):
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, list):
        return [_round_coords(x, ndigits) for x in obj]
    return obj


def _to_feature_collection(gdf, properties: list[str]) -> dict:
    fc = json.loads(gdf[properties + ["geometry"]].to_json())
    for feat in fc["features"]:
        feat["geometry"]["coordinates"] = _round_coords(
            feat["geometry"]["coordinates"]
        )
        feat.pop("id", None)
        feat.pop("bbox", None)
    fc.pop("bbox", None)
    return fc


def _write_geojson(fc: dict, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(fc, separators=(",", ":"))
    out_path.write_text(text)
    return len(text.encode())


def _simplified(gdf, tolerance: float):
    out = gdf.copy()
    out["geometry"] = out.geometry.simplify(tolerance, preserve_topology=True)
    try:
        out["geometry"] = out.geometry.make_valid()
    except AttributeError:  # older geopandas
        out["geometry"] = out.geometry.buffer(0)
    return out


def _load_districts():
    import geopandas as gpd
    import pandas as pd

    cd_zips = _download_cd_shapefiles()
    gdf = gpd.GeoDataFrame(
        pd.concat([gpd.read_file(z) for z in cd_zips], ignore_index=True)
    )
    cd_col = next(c for c in gdf.columns if c.startswith("CD") and c.endswith("FP"))
    gdf = gdf[gdf["STATEFP"].isin(STATE_FIPS)]
    gdf = gdf[~gdf[cd_col].isin(["98", "99", "ZZ"])]  # undefined/water slots
    gdf = gdf.to_crs(4326)
    gdf["state"] = gdf["STATEFP"].map(STATE_FIPS)
    gdf["district_number"] = gdf[cd_col].map(lambda cd: 0 if cd == "00" else int(cd))
    return gdf, "TIGER2025 CD119 (per-state files)"


def build_house_geojson(registry: Registry, out_path: Path,
                        size_budget_bytes: int = 4_500_000) -> dict:
    """House layer: one feature per district, tagged with seat, plan, and
    contest, simplified until the file fits the size budget."""
    gdf, source_name = _load_districts()

    contest_by_seat = {c.seat.seat_id: c for c in registry.house_contests}
    from .models import HouseSeat

    def seat_id_of(row) -> str:
        return HouseSeat(state=row["state"],
                         district_number=row["district_number"]).seat_id

    gdf["seat_id"] = gdf.apply(seat_id_of, axis=1)
    missing = set(contest_by_seat) - set(gdf["seat_id"])
    if missing:
        raise RuntimeError(
            f"TIGER file {source_name} lacks districts for seats: {sorted(missing)[:5]}..."
        )
    gdf = gdf[gdf["seat_id"].isin(contest_by_seat)]

    gdf["plan_id"] = gdf["state"].map(governing_plan_id)
    gdf["contest_id"] = gdf["seat_id"].map(
        lambda s: contest_by_seat[s].contest_id
    )
    gdf["contest_kind"] = gdf["seat_id"].map(
        lambda s: contest_kind(contest_by_seat[s])  # derived, projected for styling
    )
    gdf["geometry_may_be_superseded"] = gdf["state"].isin(MID_DECADE_STATES)

    props = ["seat_id", "state", "district_number", "plan_id", "contest_id",
             "contest_kind", "geometry_may_be_superseded"]
    # Start high-fidelity (~200 m) and coarsen only if the budget demands it:
    # districts split dense cities (e.g. OH-03/OH-15 through Columbus), so
    # aggressive tolerances visibly misassign downtown points.
    for tolerance in (0.002, 0.005, 0.01, 0.02, 0.05):
        fc = _to_feature_collection(_simplified(gdf, tolerance), props)
        fc["source"] = source_name
        fc["caveat"] = (
            "TIGER geometry may lag 2025 mid-decade plans; features with "
            "geometry_may_be_superseded=true may not reflect the operative plan"
        )
        size = _write_geojson(fc, out_path)
        if size <= size_budget_bytes:
            break
    if len(fc["features"]) != len(contest_by_seat):
        raise RuntimeError(
            f"expected {len(contest_by_seat)} district features, "
            f"got {len(fc['features'])}"
        )
    return fc


def build_states_geojson(registry: Registry, out_path: Path) -> dict:
    """Senate layer: state polygons tagged with the 2026 Senate contests
    they host (computed from the registry — never assumed)."""
    import geopandas as gpd

    state_zip = _download_first_available(STATE_URLS)
    gdf = gpd.read_file(state_zip)
    gdf = gdf[gdf["STATEFP"].isin(STATE_FIPS)].to_crs(4326)
    gdf["state"] = gdf["STATEFP"].map(STATE_FIPS)

    contests_by_state: dict[str, list] = {}
    for c in registry.senate_contests:
        contests_by_state.setdefault(c.seat.state, []).append(c)

    def ids_for(state: str) -> list[str]:
        return [c.contest_id for c in contests_by_state.get(state, [])]

    def kind_for(state: str) -> str:
        kinds = {contest_kind(c) for c in contests_by_state.get(state, [])}
        for salient in ("special", "open", "regular"):
            if salient in kinds:
                return salient
        return "none"

    gdf["senate_contest_ids"] = gdf["state"].map(ids_for)
    gdf["senate_kind"] = gdf["state"].map(kind_for)
    gdf["has_2026_senate_contest"] = gdf["senate_contest_ids"].map(bool)
    gdf["name"] = gdf["NAME"]

    fc = _to_feature_collection(
        _simplified(gdf, 0.01),
        ["state", "name", "senate_contest_ids", "senate_kind",
         "has_2026_senate_contest"],
    )
    fc["source"] = state_zip.name
    _write_geojson(fc, out_path)
    return fc
