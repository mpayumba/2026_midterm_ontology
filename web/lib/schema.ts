/**
 * Zod mirror of pipeline/models.py. The two schemas staying in sync is
 * enforced by the exported data passing BOTH: the pipeline round-trips
 * every blob through Pydantic before writing, and web/tests parses the
 * same files with these schemas.
 */
import { z } from "zod";

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export const ChamberEnum = z.enum(["senate", "house"]);
export const TriggerEnum = z.enum(["calendar", "vacancy"]);
export const TermRelationEnum = z.enum(["initiating", "completing"]);
export const StageFunctionEnum = z.enum(["nominating", "resolving", "deciding"]);
export const AggregationRuleEnum = z.enum([
  "plurality",
  "majority_runoff",
  "top_two",
  "top_four_rcv",
  "ranked_choice",
]);
export const IncumbencyStatusEnum = z.enum([
  "running",
  "retiring",
  "lost_nomination",
  "appointed_placeholder",
  "not_incumbent",
]);
export const ContestStatusEnum = z.enum([
  "scheduled",
  "ballot_set",
  "voting",
  "counting",
  "projected",
  "certified",
  "contested",
]);
export const PlanAuthorEnum = z.enum(["legislature", "commission", "court"]);

// Calendar-aware (rejects e.g. 2026-13-45), matching Pydantic's date type.
const isoDate = z.string().date();
const isoDateTime = z
  .string()
  .regex(
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$/,
    "ISO datetime"
  );

// ---------------------------------------------------------------------------
// Structural layer
// ---------------------------------------------------------------------------

export const LegalCitation = z.object({
  instrument: z.string(),
  description: z.string().nullish(),
  url: z.string().nullish(),
});

export const DistrictPlan = z.object({
  plan_id: z.string(),
  state: z.string().regex(/^[A-Z]{2}$/),
  enacted_by: PlanAuthorEnum,
  effective_from_cycle: z.number().int(),
  authorized_by: LegalCitation,
  superseded_plan_id: z.string().nullish(),
  geometry_ref: z.string().nullish(),
  litigation_pending: z.boolean(),
});

export const SenateSeat = z.object({
  chamber: z.literal("senate"),
  state: z.string().regex(/^[A-Z]{2}$/),
  senate_class: z.union([z.literal(1), z.literal(2), z.literal(3)]),
  class_grounding: LegalCitation,
  // computed on the Python side, always serialized
  seat_id: z.string(),
  division_id: z.string(),
});

export const HouseSeat = z.object({
  chamber: z.literal("house"),
  state: z.string().regex(/^[A-Z]{2}$/),
  district_number: z.number().int().min(0),
  seat_id: z.string(),
  division_id: z.string(),
});

export const Seat = z.discriminatedUnion("chamber", [SenateSeat, HouseSeat]);

export const Term = z.object({
  term_id: z.string(),
  seat_id: z.string(),
  start: isoDate,
  end: isoDate,
  occupant_person_id: z.string().nullish(),
});

// ---------------------------------------------------------------------------
// Event layer
// ---------------------------------------------------------------------------

export const VacancyEvent = z.object({
  seat_id: z.string(),
  vacated_by_person_id: z.string(),
  reason: z.string(),
  vacancy_date: isoDate,
  appointee_person_id: z.string().nullish(),
  appointed_by: z.string().nullish(),
  appointment_grounding: LegalCitation.nullish(),
});

export const Candidacy = z.object({
  person_id: z.string(),
  person_name: z.string(),
  party: z.string().nullish(),
  incumbency: IncumbencyStatusEnum,
  filing_date: isoDate.nullish(),
  stage_results: z.record(z.unknown()),
});

export const ContestStage = z
  .object({
    stage_id: z.string(),
    function: StageFunctionEnum,
    rule: AggregationRuleEnum,
    election_date: isoDate.nullish(),
    party_scope: z.string().nullish(),
    runoff_threshold: z.number().nullish(),
    advances_to: z.string().nullish(),
    statutory_basis: LegalCitation.nullish(),
    note: z.string().nullish(),
  })
  .superRefine((stage, ctx) => {
    const topN = stage.rule === "top_two" || stage.rule === "top_four_rcv";
    if (stage.function === "nominating" && stage.party_scope == null && !topN) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `nominating stage ${stage.stage_id} needs party_scope or a top-N rule`,
      });
    }
  });

// ---------------------------------------------------------------------------
// Epistemic layer — credences ABOUT contests, never fields on them
// ---------------------------------------------------------------------------

export const Annotation = z.object({
  source: z.string(),
  as_of: isoDateTime,
  kind: z.string(),
  // z.unknown() alone would let the key be absent; Pydantic requires it.
  value: z.unknown().refine((v) => v !== undefined, "value is required"),
});

// ---------------------------------------------------------------------------
// The central entity
// ---------------------------------------------------------------------------

export const Contest = z
  .object({
    contest_id: z.string(),
    cycle: z.number().int(),
    seat: Seat,
    target_term_id: z.string(),
    trigger: TriggerEnum,
    term_relation: TermRelationEnum,
    vacancy: VacancyEvent.nullish(),
    under_plan_id: z.string().nullish(),
    stages: z.array(ContestStage),
    candidacies: z.array(Candidacy),
    administered_by: z.string().nullish(),
    status: ContestStatusEnum,
    scheduling_grounding: LegalCitation.nullish(),
    annotations: z.array(Annotation),
    // computed on the Python side
    general_date: isoDate.nullish(),
    is_special: z.boolean(),
  })
  .superRefine((c, ctx) => {
    const issue = (message: string) =>
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: `${c.contest_id}: ${message}` });
    if (c.term_relation === "completing") {
      if (c.trigger !== "vacancy") issue("completing requires trigger=vacancy");
      if (c.vacancy == null) issue("completing requires an attached VacancyEvent");
    }
    if (c.vacancy != null && c.vacancy.seat_id !== c.seat.seat_id) {
      issue(
        `attached VacancyEvent is for seat ${c.vacancy.seat_id}, not this contest's seat ${c.seat.seat_id}`
      );
    }
    if (c.seat.chamber === "senate" && c.under_plan_id != null) {
      issue("Senate contests must not reference a DistrictPlan");
    }
    if (c.seat.chamber === "house" && c.under_plan_id == null) {
      issue("House contests must reference a DistrictPlan");
    }
    if (c.stages.length > 0) {
      const deciders = c.stages.filter((s) => s.function === "deciding");
      if (deciders.length !== 1) {
        issue(`stage graph must have exactly one deciding stage, found ${deciders.length}`);
      }
      const stageIds = new Set(c.stages.map((s) => s.stage_id));
      for (const s of c.stages) {
        if (s.advances_to != null && !stageIds.has(s.advances_to)) {
          issue(`stage ${s.stage_id} advances_to unknown stage ${s.advances_to}`);
        }
      }
    }
    // Serialized derived fields must agree with what the functions derive —
    // they are projections of the base facts, never trusted stored data.
    if (c.is_special !== (c.trigger === "vacancy")) {
      issue("is_special contradicts trigger (derived field out of sync)");
    }
    const decider = c.stages.find((s) => s.function === "deciding");
    if ((c.general_date ?? null) !== (decider?.election_date ?? null)) {
      issue("general_date does not match the deciding stage's election_date");
    }
    const st = c.seat.state.toLowerCase();
    const expectedSeatId =
      c.seat.chamber === "senate"
        ? `ocd-seat/us-senate/${st}/class:${c.seat.senate_class}`
        : `ocd-seat/us-house/${st}/district:${c.seat.district_number}`;
    const stateDiv = `ocd-division/country:us/state:${st}`;
    const expectedDivision =
      c.seat.chamber === "senate" || c.seat.district_number === 0
        ? stateDiv
        : `${stateDiv}/cd:${c.seat.district_number}`;
    if (c.seat.seat_id !== expectedSeatId) {
      issue(`seat_id ${c.seat.seat_id} does not match its (state, ${c.seat.chamber === "senate" ? "class" : "district"})`);
    }
    if (c.seat.division_id !== expectedDivision) {
      issue(`division_id ${c.seat.division_id} does not match the seat's constituency`);
    }
  });

export type ContestT = z.infer<typeof Contest>;
export type DistrictPlanT = z.infer<typeof DistrictPlan>;
export type TermT = z.infer<typeof Term>;
export type ContestStageT = z.infer<typeof ContestStage>;
export type CandidacyT = z.infer<typeof Candidacy>;
export type AnnotationT = z.infer<typeof Annotation>;
export type LegalCitationT = z.infer<typeof LegalCitation>;

// ---------------------------------------------------------------------------
// GeoJSON layers (the projection of the ontology onto the map)
// ---------------------------------------------------------------------------

const geometry = z.object({
  type: z.enum(["Polygon", "MultiPolygon"]),
  coordinates: z.unknown(),
});

export const HouseFeature = z.object({
  type: z.literal("Feature"),
  properties: z.object({
    seat_id: z.string(),
    state: z.string(),
    district_number: z.number().int(),
    plan_id: z.string(),
    contest_id: z.string(),
    contest_kind: z.enum(["regular", "open", "special"]),
    geometry_may_be_superseded: z.boolean(),
  }),
  geometry,
});

export const StateFeature = z.object({
  type: z.literal("Feature"),
  properties: z.object({
    state: z.string(),
    name: z.string(),
    senate_contest_ids: z.array(z.string()),
    senate_kind: z.enum(["regular", "open", "special", "none"]),
    has_2026_senate_contest: z.boolean(),
  }),
  geometry,
});

export const HouseFC = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(HouseFeature),
  source: z.string().optional(),
  caveat: z.string().optional(),
});

export const StatesFC = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(StateFeature),
  source: z.string().optional(),
});

export type HouseFeatureT = z.infer<typeof HouseFeature>;
export type StateFeatureT = z.infer<typeof StateFeature>;
export type HouseFCT = z.infer<typeof HouseFC>;
export type StatesFCT = z.infer<typeof StatesFC>;

// ---------------------------------------------------------------------------
// Derived facts — functions here too, mirroring pipeline/models.py
// ---------------------------------------------------------------------------

export function isOpenSeat(contest: ContestT): boolean {
  if (contest.candidacies.length === 0) return false;
  return !contest.candidacies.some(
    (c) => c.incumbency === "running" || c.incumbency === "appointed_placeholder"
  );
}

export function contestKind(contest: ContestT): "special" | "open" | "regular" {
  // Derive from the base fact (trigger), never from the serialized
  // is_special projection — mirroring Contest.is_special in models.py.
  if (contest.trigger === "vacancy") return "special";
  if (isOpenSeat(contest)) return "open";
  return "regular";
}

/** "MN-05", "MN at-large", or "MN Senate (Class 2)" */
export function seatLabel(contest: ContestT): string {
  const seat = contest.seat;
  if (seat.chamber === "senate") {
    return `${seat.state} Senate (Class ${seat.senate_class})`;
  }
  if (seat.district_number === 0) return `${seat.state} at-large`;
  return `${seat.state}-${String(seat.district_number).padStart(2, "0")}`;
}

/** "2023–2029" parsed from a term id like term/.../2023-2029 */
export function termYears(termId: string): string | null {
  const m = termId.match(/(\d{4})-(\d{4})$/);
  return m ? `${m[1]}–${m[2]}` : null;
}
