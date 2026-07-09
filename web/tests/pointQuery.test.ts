/**
 * Acceptance check 7 through the code path the app actually ships: the
 * turf-based queryPoint over the exported layers (the pytest twin uses
 * shapely — this one exercises the client-side implementation).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { queryPoint } from "../lib/pointQuery";
import { HouseFC, StatesFC } from "../lib/schema";

const DATA_DIR = join(__dirname, "..", "public", "data");
const houseFC = HouseFC.parse(
  JSON.parse(readFileSync(join(DATA_DIR, "house_districts.geojson"), "utf-8"))
);
const statesFC = StatesFC.parse(
  JSON.parse(readFileSync(join(DATA_DIR, "states_senate.geojson"), "utf-8"))
);

describe("queryPoint (the shipped client-side point query)", () => {
  it("downtown Minneapolis -> exactly MN-05 + the MN Class 2 contest", () => {
    const result = queryPoint(-93.265, 44.9778, houseFC, statesFC);
    expect(result.houseFeatures.map((f) => f.properties.seat_id)).toEqual([
      "ocd-seat/us-house/mn/district:5",
    ]);
    expect(result.stateFeatures.map((f) => f.properties.state)).toEqual(["MN"]);
    expect(result.contestIds).toEqual([
      "contest/2026/us-house/mn/district:5",
      "contest/2026/us-senate/mn/class:2",
    ]);
  });

  it("East Broad St, Columbus -> exactly OH-03 + the OH Class 3 special", () => {
    const result = queryPoint(-82.97, 39.965, houseFC, statesFC);
    expect(result.contestIds).toEqual([
      "contest/2026/us-house/oh/district:3",
      "contest/2026/us-senate/oh/class:3/special",
    ]);
    // TIGER lags Ohio's 2025 mid-decade plan: the flag must ride along.
    expect(result.houseFeatures[0].properties.geometry_may_be_superseded).toBe(true);
  });

  it("the open Atlantic -> nothing on the ballot", () => {
    const result = queryPoint(-40, 35, houseFC, statesFC);
    expect(result.contestIds).toEqual([]);
  });
});
