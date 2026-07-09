/**
 * The core interaction: "what's on the ballot at this location?"
 * Client-side point-in-polygon over both layers — every view is a
 * projection of the contest set.
 */
import booleanPointInPolygon from "@turf/boolean-point-in-polygon";
import type { HouseFCT, HouseFeatureT, StateFeatureT, StatesFCT } from "./schema";

export interface PointQueryResult {
  houseFeatures: HouseFeatureT[];
  stateFeatures: StateFeatureT[];
  /** House first, then Senate: the ballot stack at this point. */
  contestIds: string[];
}

export function queryPoint(
  lng: number,
  lat: number,
  houseFC: HouseFCT,
  statesFC: StatesFCT
): PointQueryResult {
  const point: [number, number] = [lng, lat];

  const houseFeatures = houseFC.features.filter((f) =>
    booleanPointInPolygon(point, f as never)
  );
  const stateFeatures = statesFC.features.filter((f) =>
    booleanPointInPolygon(point, f as never)
  );

  const contestIds = [
    ...houseFeatures.map((f) => f.properties.contest_id),
    ...stateFeatures.flatMap((f) => f.properties.senate_contest_ids),
  ];

  return { houseFeatures, stateFeatures, contestIds };
}
