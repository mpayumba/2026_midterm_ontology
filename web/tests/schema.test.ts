/**
 * Acceptance check 6: every exported JSON file round-trips through the Zod
 * mirror. The pipeline validated these blobs against the Pydantic models
 * before writing; if both parsers accept them, the schemas are in sync.
 */
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import {
  Contest,
  DistrictPlan,
  HouseFC,
  StatesFC,
  Term,
  contestKind,
} from "../lib/schema";

const DATA_DIR = join(__dirname, "..", "public", "data");

function load(name: string): unknown {
  const path = join(DATA_DIR, name);
  if (!existsSync(path)) {
    throw new Error(`${path} missing — run \`python -m pipeline.export\` first`);
  }
  return JSON.parse(readFileSync(path, "utf-8"));
}

describe("exported data round-trips through the Zod schema", () => {
  it("contests.json parses and has the derived 2026 shape", () => {
    const contests = z.array(Contest).parse(load("contests.json"));
    expect(contests).toHaveLength(470);

    const senate = contests.filter((c) => c.seat.chamber === "senate");
    const house = contests.filter((c) => c.seat.chamber === "house");
    expect(house).toHaveLength(435);
    expect(senate).toHaveLength(35);

    const specials = senate.filter((c) => c.is_special);
    expect(specials).toHaveLength(2);
    for (const s of specials) {
      expect(s.term_relation).toBe("completing");
      expect(s.target_term_id).toMatch(/2023-2029$/);
      expect(s.vacancy).toBeTruthy();
      expect(contestKind(s)).toBe("special");
    }

    // the discriminated union discriminates
    for (const c of senate) expect(c.under_plan_id).toBeNull();
    for (const c of house) expect(c.under_plan_id).toBeTruthy();
  });

  it("plans.json parses; mid-decade plans supersede 2021 plans", () => {
    const plans = z.array(DistrictPlan).parse(load("plans.json"));
    expect(plans).toHaveLength(56);
    const midDecade = plans.filter((p) => p.effective_from_cycle === 2026);
    expect(midDecade.map((p) => p.state).sort()).toEqual(
      ["CA", "MO", "NC", "OH", "TX", "UT"]
    );
    for (const p of midDecade) {
      expect(p.superseded_plan_id).toBe(`${p.state.toLowerCase()}-cd-2021`);
    }
  });

  it("terms.json parses", () => {
    const terms = z.array(Term).parse(load("terms.json"));
    expect(terms.length).toBeGreaterThanOrEqual(470);
  });

  it("house_districts.geojson parses with 435 tagged features", () => {
    const fc = HouseFC.parse(load("house_districts.geojson"));
    expect(fc.features).toHaveLength(435);
    for (const f of fc.features) {
      expect(f.properties.plan_id).toBeTruthy();
    }
  });

  it("states_senate.geojson parses with 50 features", () => {
    const fc = StatesFC.parse(load("states_senate.geojson"));
    expect(fc.features).toHaveLength(50);
    const withContest = fc.features.filter(
      (f) => f.properties.has_2026_senate_contest
    );
    // 33 Class 2 states + FL + OH (neither hosts a Class 2 seat) = 35 states
    expect(withContest).toHaveLength(35);
  });
});
