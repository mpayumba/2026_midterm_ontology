"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ContestMap, { KIND_COLORS } from "@/components/Map";
import ContestPanel from "@/components/ContestPanel";
import { queryPoint } from "@/lib/pointQuery";
import {
  Contest,
  DistrictPlan,
  HouseFC,
  StatesFC,
  type ContestT,
  type DistrictPlanT,
  type HouseFCT,
  type StatesFCT,
} from "@/lib/schema";
import { z } from "zod";

interface Data {
  contests: ContestT[];
  plans: Map<string, DistrictPlanT>;
  houseFC: HouseFCT;
  statesFC: StatesFCT;
}

async function loadData(): Promise<Data> {
  const [contestsRaw, plansRaw, houseRaw, statesRaw] = await Promise.all(
    ["contests.json", "plans.json", "house_districts.geojson", "states_senate.geojson"].map(
      (f) => fetch(`/data/${f}`).then((r) => {
        if (!r.ok) throw new Error(`failed to load ${f}: ${r.status}`);
        return r.json();
      })
    )
  );
  // The web side re-validates the pipeline's output: the static files are
  // the contract, and both schemas must accept them.
  const contests = z.array(Contest).parse(contestsRaw);
  const plans = z.array(DistrictPlan).parse(plansRaw);
  return {
    contests,
    plans: new Map(plans.map((p) => [p.plan_id, p])),
    houseFC: HouseFC.parse(houseRaw),
    statesFC: StatesFC.parse(statesRaw),
  };
}

export default function Home() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showHouse, setShowHouse] = useState(true);
  const [showSenate, setShowSenate] = useState(true);
  const [picked, setPicked] = useState<{ lng: number; lat: number } | null>(null);

  useEffect(() => {
    loadData().then(setData).catch((e) => setError(String(e)));
  }, []);

  // Deep link: /?lng=-93.265&lat=44.978 runs the point query on load.
  useEffect(() => {
    if (!data) return;
    const params = new URLSearchParams(window.location.search);
    const lng = parseFloat(params.get("lng") ?? "");
    const lat = parseFloat(params.get("lat") ?? "");
    if (Number.isFinite(lng) && Number.isFinite(lat)) setPicked({ lng, lat });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const contestById = useMemo(
    () => new Map((data?.contests ?? []).map((c) => [c.contest_id, c])),
    [data]
  );

  const handlePick = useCallback((lng: number, lat: number) => {
    setPicked({ lng, lat });
    const url = new URL(window.location.href);
    url.searchParams.set("lng", lng.toFixed(5));
    url.searchParams.set("lat", lat.toFixed(5));
    window.history.replaceState(null, "", url);
  }, []);

  const selection = useMemo(() => {
    if (!data || !picked) return null;
    const result = queryPoint(picked.lng, picked.lat, data.houseFC, data.statesFC);
    const contests = result.contestIds
      .map((id) => contestById.get(id))
      .filter((c): c is ContestT => c !== undefined);
    const geometryMayBeSuperseded = result.houseFeatures.some(
      (f) => f.properties.geometry_may_be_superseded
    );
    return { point: picked, contests, geometryMayBeSuperseded };
  }, [data, picked, contestById]);

  if (error) {
    return (
      <div className="loading-screen">
        Failed to load data: {error}. Run `python -m pipeline.export` first.
      </div>
    );
  }
  if (!data) {
    return <div className="loading-screen">Loading the 2026 contest set…</div>;
  }

  return (
    <main className="app">
      <div className="map-container">
        <ContestMap
          houseFC={data.houseFC}
          statesFC={data.statesFC}
          showHouse={showHouse}
          showSenate={showSenate}
          marker={picked}
          onPick={handlePick}
        />
      </div>

      <div className="controls">
        <h1>2026 Midterm Ontology</h1>
        <div className="subtitle">
          {data.contests.length} congressional contests, legally grounded
        </div>
        <label>
          <input
            type="checkbox"
            checked={showHouse}
            onChange={(e) => setShowHouse(e.target.checked)}
          />
          House districts (435)
        </label>
        <label>
          <input
            type="checkbox"
            checked={showSenate}
            onChange={(e) => setShowSenate(e.target.checked)}
          />
          Senate contests (35 seats up)
        </label>
        <div className="legend">
          <div className="item">
            <span className="swatch" style={{ background: KIND_COLORS.regular }} />
            Regular contest
          </div>
          <div className="item">
            <span className="swatch" style={{ background: KIND_COLORS.special }} />
            Special (vacancy, term-completing)
          </div>
          <div className="item">
            <span className="swatch" style={{ background: KIND_COLORS.open }} />
            Open seat (incumbent not running)
          </div>
        </div>
        <div className="hint">Click anywhere: what’s on the ballot there?</div>
      </div>

      {selection && (
        <ContestPanel
          contests={selection.contests}
          plans={data.plans}
          point={selection.point}
          caveat={data.houseFC.caveat}
          geometryMayBeSuperseded={selection.geometryMayBeSuperseded}
          onClose={() => setPicked(null)}
        />
      )}
    </main>
  );
}
