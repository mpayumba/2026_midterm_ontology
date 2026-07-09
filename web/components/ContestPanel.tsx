"use client";

import type {
  AnnotationT,
  ContestStageT,
  ContestT,
  DistrictPlanT,
  LegalCitationT,
} from "@/lib/schema";
import { contestKind, seatLabel, termYears } from "@/lib/schema";

const STAGE_LABEL: Record<string, string> = {
  nominating: "Primary",
  resolving: "Runoff",
  deciding: "General",
};

const RULE_LABEL: Record<string, string> = {
  plurality: "plurality",
  majority_runoff: "majority (runoff below threshold)",
  top_two: "top-two",
  top_four_rcv: "top-four / ranked choice",
};

const INCUMBENCY_LABEL: Record<string, string> = {
  running: "incumbent, running",
  retiring: "incumbent, retiring",
  lost_nomination: "incumbent, lost nomination",
  appointed_placeholder: "appointed incumbent",
  not_incumbent: "",
};

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "date TBD";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function stageSortKey(s: ContestStageT): string {
  const fnOrder = { nominating: 0, resolving: 1, deciding: 2 }[s.function];
  return `${s.election_date ?? "9999-99-99"}|${fnOrder}|${s.stage_id}`;
}

function StageRow({ stage }: { stage: ContestStageT }) {
  const conditional = stage.note?.includes("onditionally reachable");
  return (
    <div className={`stage fn-${stage.function}`}>
      <div className="dot" />
      <div>
        <span className="what">
          {STAGE_LABEL[stage.function]}
          {stage.party_scope ? ` (${stage.party_scope})` : ""}
        </span>{" "}
        <span className="meta">
          — {fmtDate(stage.election_date)} · {RULE_LABEL[stage.rule] ?? stage.rule}
          {stage.runoff_threshold != null &&
            ` · ${Math.round(stage.runoff_threshold * 100)}% threshold`}
        </span>
        {conditional && <div className="conditional">{stage.note}</div>}
        {!conditional && stage.note && <div className="meta">{stage.note}</div>}
      </div>
    </div>
  );
}

function Assessments({ annotations }: { annotations: AnnotationT[] }) {
  if (annotations.length === 0) return null;
  return (
    <div className="assessments">
      <h4>Assessments — epistemic layer</h4>
      {annotations.map((a, i) => (
        <div key={i} className="assessment">
          <strong>{String(a.value)}</strong> ({a.kind}){" "}
          <span className="source">
            — {a.source}, as of {a.as_of.slice(0, 10)}
          </span>
        </div>
      ))}
    </div>
  );
}

function collectCitations(
  contest: ContestT,
  plan: DistrictPlanT | undefined
): LegalCitationT[] {
  const seen = new Set<string>();
  const out: LegalCitationT[] = [];
  const push = (c: LegalCitationT | null | undefined) => {
    if (!c || seen.has(c.instrument)) return;
    seen.add(c.instrument);
    out.push(c);
  };
  if (contest.seat.chamber === "senate") push(contest.seat.class_grounding);
  push(contest.vacancy?.appointment_grounding);
  push(plan?.authorized_by);
  push(contest.scheduling_grounding);
  for (const s of contest.stages) push(s.statutory_basis);
  return out;
}

export function ContestCard({
  contest,
  plan,
}: {
  contest: ContestT;
  plan: DistrictPlanT | undefined;
}) {
  const kind = contestKind(contest);
  const stages = [...contest.stages].sort((a, b) =>
    stageSortKey(a).localeCompare(stageSortKey(b))
  );
  const years = termYears(contest.target_term_id);
  const citations = collectCitations(contest, plan);

  return (
    <article className={`contest-card kind-${kind}`}>
      <div className="stripe" />
      <div className="body">
        <div className="card-title-row">
          <h3>{seatLabel(contest)}</h3>
          <span className={`badge badge-${contest.is_special ? "special" : "regular"}`}>
            {contest.is_special ? "Special" : "Regular"}
          </span>
          {kind === "open" && <span className="badge badge-open">Open seat</span>}
        </div>
        <div className="contest-id">{contest.contest_id}</div>

        {contest.term_relation === "completing" ? (
          <div className="term-line completing">
            <strong>Fills the remainder of the {years} term</strong> — the same
            term the vacating senator was elected to, not a new one.
            {contest.vacancy && (
              <div className="vacancy-note">
                Vacated {fmtDate(contest.vacancy.vacancy_date)} (
                {contest.vacancy.reason.toLowerCase().replace(/^resigned/, "resigned")});{" "}
                {contest.vacancy.appointed_by
                  ? `placeholder appointed by ${contest.vacancy.appointed_by}`
                  : "no appointment recorded"}
                .
              </div>
            )}
          </div>
        ) : (
          <div className="term-line">
            Initiates the new {years} term
            {contest.seat.chamber === "senate"
              ? ` (six-year Senate term, Class ${contest.seat.senate_class})`
              : " (two-year House term)"}
            .
          </div>
        )}

        <section className="block">
          <h4>Stage timeline</h4>
          {stages.map((s) => (
            <StageRow key={s.stage_id} stage={s} />
          ))}
        </section>

        {contest.candidacies.length > 0 && (
          <section className="block">
            <h4>Candidacies</h4>
            {contest.candidacies.map((c) => (
              <div key={c.person_id} className="candidacy">
                {c.party && <span className="party">{c.party}</span>}
                <span>{c.person_name}</span>
                {INCUMBENCY_LABEL[c.incumbency] && (
                  <span className="incumbency">{INCUMBENCY_LABEL[c.incumbency]}</span>
                )}
              </div>
            ))}
          </section>
        )}

        {contest.seat.chamber === "house" && plan && (
          <section className="block">
            <h4>Governing district plan</h4>
            <div style={{ fontSize: 12.5, color: "#475569" }}>
              <code>{plan.plan_id}</code> · enacted by {plan.enacted_by}
              {plan.superseded_plan_id && (
                <> · supersedes <code>{plan.superseded_plan_id}</code></>
              )}
              {plan.litigation_pending && <span className="warn">litigation pending</span>}
            </div>
          </section>
        )}

        <Assessments annotations={contest.annotations} />

        {citations.length > 0 && (
          <div className="legal-basis">
            <h4>Legal basis</h4>
            <ol>
              {citations.map((c, i) => (
                <li key={i}>
                  <span className="instrument">{c.instrument}</span>
                  {c.description ? ` — ${c.description}` : ""}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </article>
  );
}

export default function ContestPanel({
  contests,
  plans,
  point,
  caveat,
  onClose,
}: {
  contests: ContestT[];
  plans: Map<string, DistrictPlanT>;
  point: { lng: number; lat: number };
  caveat?: string;
  onClose: () => void;
}) {
  const anySuperseded = contests.some(
    (c) => c.under_plan_id && plans.get(c.under_plan_id)?.effective_from_cycle === 2026
  );
  return (
    <aside className="panel">
      <div className="panel-header">
        <h2>On the ballot here</h2>
        <span className="coords">
          {point.lat.toFixed(4)}, {point.lng.toFixed(4)}
        </span>
        <button className="panel-close" onClick={onClose} aria-label="Close panel">
          ×
        </button>
      </div>
      {contests.length === 0 ? (
        <div className="panel-empty">
          No 2026 congressional contest at this point — try clicking inside a
          U.S. state.
        </div>
      ) : (
        contests.map((c) => (
          <ContestCard
            key={c.contest_id}
            contest={c}
            plan={c.under_plan_id ? plans.get(c.under_plan_id) : undefined}
          />
        ))
      )}
      {anySuperseded && caveat && (
        <div className="vacancy-note" style={{ marginTop: 8 }}>
          ⚠ {caveat}
        </div>
      )}
    </aside>
  );
}
