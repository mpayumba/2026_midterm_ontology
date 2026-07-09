"""Emit the static-file contract consumed by the web app.

Every blob is round-tripped through the Pydantic models before writing;
the web side re-parses the same files with the Zod mirror — the two
schemas staying in sync is enforced by the data passing both.

Run:  python -m pipeline.export
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Contest, DistrictPlan, Term
from .registry import Registry, build_registry

WEB_DATA_DIR = Path(__file__).resolve().parent.parent / "web" / "public" / "data"


def _validated_dump(model_cls, objs) -> list[dict]:
    """Serialize and re-validate each object: the JSON we ship must itself
    parse back into the ontology."""
    dumped = []
    for obj in objs:
        blob = json.loads(obj.model_dump_json())
        model_cls.model_validate(blob)
        dumped.append(blob)
    return dumped


def _write(name: str, payload) -> Path:
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = WEB_DATA_DIR / name
    path.write_text(json.dumps(payload, indent=None, separators=(",", ":")))
    return path


def export_registry(registry: Registry) -> None:
    _write("contests.json", _validated_dump(Contest, registry.contests))
    _write("plans.json", _validated_dump(DistrictPlan, registry.plans.values()))
    _write("terms.json", _validated_dump(Term, registry.terms))


def export_geometries(registry: Registry) -> None:
    from .geo import build_house_geojson, build_states_geojson

    build_house_geojson(registry, WEB_DATA_DIR / "house_districts.geojson")
    build_states_geojson(registry, WEB_DATA_DIR / "states_senate.geojson")


def main() -> None:
    registry = build_registry()
    n_sen = len(registry.senate_contests)
    n_spec = sum(1 for c in registry.senate_contests if c.is_special)
    print(f"registry: {len(registry.contests)} contests "
          f"({n_sen} senate, {n_spec} special, "
          f"{len(registry.house_contests)} house), "
          f"{len(registry.plans)} plans, {len(registry.terms)} terms")
    export_registry(registry)
    print(f"wrote contests.json / plans.json / terms.json -> {WEB_DATA_DIR}")
    export_geometries(registry)
    for f in sorted(WEB_DATA_DIR.glob("*")):
        print(f"  {f.name}: {f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
