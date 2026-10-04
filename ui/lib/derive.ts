import type { ConfigRow, Decision, Ledger, Spend, TokenRow } from "./ledger";

// Everything the page shows is computed here from the two ledger files, so the
// page can never show something the agent did not log.

export type Outcome = "kept" | "skipped" | "acted" | "error" | "info";

export type Entry = Decision & { id: string; outcome: Outcome; day: string };

export type Stage = { key: string; label: string; count: number; note: string; phases: string[] };

export type Credit = {
  provider: string;
  name: string;
  unit: "usd" | "credits";
  left: number | null;
  limit: number | null;
  spent: number;
  hours: number | null;
  // From the Lambda row's source: "... <name> running since 2026-10-02 18:28 UTC".
  runningSince: string | null;
  // First day the Lambda cost switched from uptime to wall-clock billing; that day carries the catch-up.
  billingChangedOn: string | null;
  fromProvider: boolean;
  source: string;
  daily: { day: string; amount: number }[];
  runsOut: string;
  asOf: string;
};

export type Health = {
  lastActivity: string | null;
  currentRun: string | null;
  runState: RunState | "no runs yet";
  runsToday: number;
  errors24h: Entry[];
};

export type RunState = "running" | "finished" | "stopped by budget" | "stalled" | "failed";

export type RunRow = {
  run: string;
  started: string;
  lastRow: string;
  state: RunState;
  stateWhy: string;
  found: number;
  attempted: number;
  passedGate: number;
  opened: number;
  merged: number;
  closed: number;
  rejected: number;
  tokens: number | null;
  costUsd: number | null;
  config: { key: string; value: string }[];
  issues: IssueWork[];
  // Token use the agent couldn't tie to one issue (subject "-"), e.g. a whole cron job.
  runWide: StepUse[];
};

export type StepUse = { step: string; model: string; tokens: number; costUsd: number; result: string | null };

export type IssueWork = { subject: string; outcome: string; tone: "ok" | "info" | "bad" | "warn" | "muted"; steps: StepUse[]; costUsd: number | null };

export type Rejection = { ts: string; run: string; subject: string; phase: string; reason: string; evidence: string };

export type ModelUse = { model: string; runs: number; tokensIn: number; tokensOut: number; costUsd: number };

export type DayTotals = { day: string; huggingface: number; lambda: number; firecrawl: number; prs: number };

export type RepoRow = { repo: string; verdict: string; text: string; files: string; checked: string; prs: number };

export type View = {
  origin: Ledger["origin"];
  fetchedAt: string;
  now: string;
  days: string[];
  entries: Entry[];
  stagesByDay: Record<string, Stage[]>;
  credits: Credit[];
  history: DayTotals[];
  runs: RunRow[];
  rejections: Rejection[];
  models: ModelUse[];
  tokensFromSample: boolean;
  health: Health;
  repos: RepoRow[];
};

const ACTED = new Set(["pr.opened", "claim.posted", "follow-up.reply", "follow-up.push"]);
const SKIPPED = new Set(["skipped", "dropped", "skip", "refused", "already fixed", "bans", "unclear", "abandoned", "cap reached", "ended run", "idle"]);
const KEPT = new Set(["kept", "take", "allows", "allows-with-disclosure", "pass", "precedent found", "ready", "ok"]);

export function outcomeOf(d: Decision): Outcome {
  if (d.result === "error" || d.phase.endsWith(".error")) return "error";
  if (ACTED.has(d.phase)) return "acted";
  if (SKIPPED.has(d.result)) return "skipped";
  if (KEPT.has(d.result)) return "kept";
  return "info";
}

const day = (ts: string) => ts.slice(0, 10);
const issueRepo = (subject: string) => subject.split("#")[0];

function stages(rows: Decision[]): Stage[] {
  const by = (phase: string, result?: string) => rows.filter((r) => r.phase === phase && (result === undefined || r.result === result));
  const verify = by("discover.verify");
  const kept = verify.filter((r) => r.result === "kept");
  const dropReasons = countBy(verify.filter((r) => r.result === "dropped").map((r) => r.decision.replace(/^dropped:\s*/, "")));
  const policy = latestPer(by("policy"), (r) => r.subject);
  const allowed = policy.filter((r) => r.result.startsWith("allows"));
  const notAllowed = countBy(policy.filter((r) => !r.result.startsWith("allows")).map((r) => r.result));
  const takes = by("triage", "take");
  const skips = by("triage", "skip");
  const claims = by("claim.posted");
  const fixed = new Set(rows.filter((r) => r.phase.startsWith("fix.")).map((r) => r.subject));
  // An issue claimed and then fixed the same day is one issue worked on, and no longer waiting.
  const worked = new Set([...fixed, ...claims.map((c) => c.subject)]);
  const waiting = claims.filter((c) => !fixed.has(c.subject)).length;
  const abandoned = by("fix.abandoned");
  const opened = by("pr.opened");
  const refused = by("pr.refused");
  return [
    { key: "found", label: "Issues checked", count: verify.length, note: verify.length ? `${verify.length - kept.length} dropped${dropReasons ? ` · ${dropReasons}` : ""}` : "no discovery", phases: ["discover.query", "discover.verify", "discover.seen", "discover.precedent", "discover.summary"] },
    { key: "kept", label: "Still open", count: kept.length, note: "unassigned, no open PR", phases: ["discover.verify"] },
    { key: "policy", label: "Repos allow AI", count: allowed.length, note: notAllowed || `of ${policy.length} repos checked`, phases: ["policy"] },
    { key: "triage", label: "Chosen", count: takes.length, note: `${skips.length} skipped in triage`, phases: ["triage"] },
    { key: "work", label: "Worked on", count: worked.size, note: `${waiting} claim${waiting === 1 ? "" : "s"} waiting · ${abandoned.length} abandoned`, phases: ["claim.posted", "claim.status", "fix.workspace", "fix.setup", "fix.test.baseline", "fix.test.after", "fix.abandoned", "gate"] },
    { key: "pr", label: "PRs opened", count: opened.length, note: refused.length ? `${refused.length} refused by the gate` : "after the self-review gate", phases: ["pr.opened", "pr.refused", "follow-up.reply", "follow-up.push", "follow-up.ack"] },
  ];
}

function countBy(xs: string[]): string {
  const m = new Map<string, number>();
  for (const x of xs) m.set(x, (m.get(x) ?? 0) + 1);
  return [...m].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, n]) => `${n} ${k}`).join(", ");
}

function latestPer<T extends { ts: string }>(xs: T[], key: (x: T) => string): T[] {
  const m = new Map<string, T>();
  for (const x of xs) if (!m.has(key(x)) || m.get(key(x))!.ts < x.ts) m.set(key(x), x);
  return [...m.values()];
}

const NAMES: Record<string, string> = { huggingface: "Hugging Face", lambda: "Lambda", firecrawl: "Firecrawl" };
const ORDER = ["huggingface", "lambda", "firecrawl"];

const isDollars = (provider: string) => provider !== "firecrawl";

function daysBetween(from: string, to: string): string[] {
  const out: string[] = [];
  for (let t = Date.parse(`${from}T00:00:00Z`); t <= Date.parse(`${to}T00:00:00Z`); t += 86400_000) out.push(day(new Date(t).toISOString()));
  return out;
}

// spend.tsv rows are running totals (month to date, or all time for Lambda),
// so a day's spend is the change from the previous day's last row.
function spendPerDay(spend: Spend[], provider: string, days: string[]): { day: string; amount: number }[] {
  const value = (s: Spend) => (isDollars(provider) ? s.cost_usd : s.used);
  const endOfDay = new Map<string, number>();
  for (const r of spend.filter((s) => s.provider === provider).sort((a, b) => a.ts.localeCompare(b.ts))) endOfDay.set(day(r.ts), value(r));
  const known = [...endOfDay.keys()].sort();
  return days.map((d) => {
    const cur = endOfDay.get(d);
    if (cur === undefined) return { day: d, amount: 0 };
    const before = known.filter((k) => k < d).at(-1);
    const prev = before ? endOfDay.get(before)! : 0;
    // Hugging Face and Firecrawl report month-to-date totals, so a new month starts from zero.
    // A drop also means the running total was reset; either way the new total is that day's spend.
    const newMonth = provider !== "lambda" && before !== undefined && before.slice(0, 7) !== d.slice(0, 7);
    return { day: d, amount: !newMonth && cur >= prev ? cur - prev : cur };
  });
}

function credits(spend: Spend[], now: string): Credit[] {
  const last7 = Array.from({ length: 7 }, (_, i) => day(new Date(Date.parse(now) - (6 - i) * 86400_000).toISOString()));
  return ORDER.filter((p) => spend.some((s) => s.provider === p)).map((provider) => {
    const rows = spend.filter((s) => s.provider === provider).sort((a, b) => a.ts.localeCompare(b.ts));
    const latest = rows[rows.length - 1];
    const dollars = isDollars(provider);
    const value = (s: Spend) => (dollars ? s.cost_usd : s.used);
    const daily = spendPerDay(spend, provider, last7);
    const left = latest.remaining;
    const recent = daily.slice(-3).map((d) => d.amount);
    const rate = recent.reduce((a, b) => a + b, 0) / recent.length;
    const runsOut = left === null ? "unknown" : rate <= 0 ? "not at the current rate" : formatRunout(now, left / rate);
    return {
      provider,
      name: NAMES[provider] ?? provider,
      unit: dollars ? "usd" : "credits",
      left,
      limit: latest.limit,
      spent: value(latest),
      hours: provider === "lambda" ? latest.used : null,
      runningSince: latest.source.match(/running since (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC/)?.[1] ?? null,
      billingChangedOn:
        provider === "lambda" && rows.some((r) => r.source.includes("uptime"))
          ? day(rows.find((r) => r.source.includes("wall-clock"))?.ts ?? "") || null
          : null,
      fromProvider: latest.source.startsWith("api"),
      source: latest.source,
      daily,
      runsOut,
      asOf: latest.ts,
    };
  });
}

function formatRunout(now: string, days: number): string {
  if (days > 60) return "not for 2+ months at this rate";
  const d = new Date(Date.parse(now) + days * 86400_000);
  return `~${d.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })} at this rate`;
}

function history(spend: Spend[], entries: Entry[], now: string): DayTotals[] {
  const first = [spend[0]?.ts, entries[0]?.ts].filter((t): t is string => !!t).map(day).sort()[0];
  if (!first) return [];
  const days = daysBetween(first, day(now));
  const per = Object.fromEntries(ORDER.map((p) => [p, spendPerDay(spend, p, days)]));
  return days.map((d, i) => ({
    day: d,
    huggingface: per.huggingface[i].amount,
    lambda: per.lambda[i].amount,
    firecrawl: per.firecrawl[i].amount,
    prs: entries.filter((e) => e.day === d && e.phase === "pr.opened").length,
  }));
}

// A run with no run.end whose newest row is this old has stopped making progress
// (a crash, or a prompt waiting for approval that never comes).
const STALL_MS = 2 * 60 * 60 * 1000;

const STEP_ORDER = ["discover", "triage", "claim", "fix", "gate", "follow-up", "summary"];
const stepRank = (s: string) => (STEP_ORDER.indexOf(s) + 1 || 99);

function issueWork(run: string, rows: Entry[], tokens: TokenRow[], outcomes: Entry[]): IssueWork[] {
  // Issues the run did real work on: chosen in triage, claimed, or fixed.
  const subjects = [...new Set(rows.filter((e) => (e.phase === "triage" && e.result === "take") || e.phase.startsWith("fix.") || e.phase === "claim.posted" || e.phase === "gate").map((e) => e.subject))];
  return subjects.map((subject) => {
    const mine = rows.filter((e) => e.subject === subject);
    const has = (phase: string) => mine.find((e) => e.phase === phase);
    const opened = has("pr.opened");
    const merged = opened && outcomes.find((o) => o.subject === subject && o.result === "merged");
    const closed = opened && outcomes.find((o) => o.subject === subject && o.result === "closed");
    const gate = mine.findLast((e) => e.phase === "gate");
    let outcome = "in progress";
    let tone: IssueWork["tone"] = "muted";
    if (merged) [outcome, tone] = [merged.decision, "ok"];
    else if (closed) [outcome, tone] = [closed.decision, "warn"];
    else if (opened) [outcome, tone] = [opened.decision, "info"];
    else if (gate && gate.result !== "pass") [outcome, tone] = ["rejected by gate", "bad"];
    else if (has("pr.refused")) [outcome, tone] = ["PR refused", "bad"];
    else if (has("fix.abandoned")) [outcome, tone] = ["fix abandoned", "warn"];
    else if (has("claim.posted")) [outcome, tone] = ["claim waiting", "info"];
    const t = tokens.filter((x) => x.run === run && x.subject === subject);
    const steps = t
      .map((x) => ({ step: x.step, model: x.model, tokens: x.tokens_in + x.tokens_out, costUsd: x.cost_usd, result: x.step === "gate" && gate ? gate.result : null }))
      .sort((a, b) => stepRank(a.step) - stepRank(b.step));
    return { subject, outcome, tone, steps, costUsd: t.length ? t.reduce((a, x) => a + x.cost_usd, 0) : null };
  });
}

function runs(entries: Entry[], tokens: TokenRow[], config: ConfigRow[], now: string): RunRow[] {
  const ids = [...new Set(entries.map((e) => e.run).filter(Boolean))];
  // pr.outcome rows can land in a later run than the PR, so match them by issue.
  const outcomes = entries.filter((e) => e.phase === "pr.outcome");
  return ids
    .map((run) => {
      const rows = entries.filter((e) => e.run === run);
      const by = (phase: string) => rows.filter((e) => e.phase === phase);
      const opened = by("pr.opened");
      const outcomeOf = (r: string) => outcomes.filter((o) => opened.some((p) => p.subject === o.subject) && o.result === r).length;
      const lastRow = rows.at(-1)!.ts;
      const errors = rows.filter((e) => e.outcome === "error");
      const guard = rows.find((e) => e.phase === "guard" && e.result === "skipped");
      let state: RunState = "running";
      let stateWhy = "no run.end yet";
      if (guard) [state, stateWhy] = ["stopped by budget", guard.why];
      else if (rows.some((e) => e.phase === "run.end")) [state, stateWhy] = ["finished", rows.findLast((e) => e.phase === "run.end")!.why];
      else if (Date.parse(now) - Date.parse(lastRow) > STALL_MS)
        [state, stateWhy] = errors.length ? ["failed", errors.at(-1)!.why] : ["stalled", `no new rows since ${lastRow.slice(11, 16)} UTC; last step ${rows.at(-1)!.phase}`];
      const t = tokens.filter((x) => x.run === run);
      return {
        run,
        started: rows[0].ts,
        lastRow,
        state,
        stateWhy,
        found: by("discover.verify").length,
        attempted: new Set(rows.filter((e) => e.phase.startsWith("fix.")).map((e) => e.subject)).size,
        passedGate: by("gate").filter((e) => e.result === "pass").length,
        opened: opened.length,
        merged: outcomeOf("merged"),
        closed: outcomeOf("closed"),
        rejected: by("gate").filter((e) => e.result !== "pass").length + by("pr.refused").filter((e) => !by("gate").some((g) => g.subject === e.subject && g.result !== "pass")).length,
        tokens: t.length ? t.reduce((a, x) => a + x.tokens_in + x.tokens_out, 0) : null,
        costUsd: t.length ? t.reduce((a, x) => a + x.cost_usd, 0) : null,
        config: config.filter((c) => c.run === run).map(({ key, value }) => ({ key, value })),
        issues: issueWork(run, rows, tokens, outcomes),
        runWide: t
          .filter((x) => x.subject === "-")
          .map((x) => ({ step: x.step, model: x.model, tokens: x.tokens_in + x.tokens_out, costUsd: x.cost_usd, result: null }))
          .sort((a, b) => stepRank(a.step) - stepRank(b.step)),
      };
    })
    .sort((a, b) => b.started.localeCompare(a.started));
}

function rejections(entries: Entry[]): Rejection[] {
  const gateFails = entries.filter((e) => e.phase === "gate" && e.result !== "pass");
  const refused = entries.filter((e) => e.phase === "pr.refused" && !gateFails.some((g) => g.subject === e.subject && g.run === e.run));
  return [...gateFails, ...refused]
    .map((e) => ({ ts: e.ts, run: e.run, subject: e.subject, phase: e.phase, reason: e.why, evidence: e.evidence }))
    .sort((a, b) => b.ts.localeCompare(a.ts));
}

function models(tokens: TokenRow[]): ModelUse[] {
  const m = new Map<string, ModelUse & { runSet: Set<string> }>();
  for (const t of tokens) {
    const u = m.get(t.model) ?? { model: t.model, runs: 0, tokensIn: 0, tokensOut: 0, costUsd: 0, runSet: new Set<string>() };
    u.tokensIn += t.tokens_in;
    u.tokensOut += t.tokens_out;
    u.costUsd += t.cost_usd;
    u.runSet.add(t.run);
    m.set(t.model, u);
  }
  return [...m.values()].map(({ runSet, ...u }) => ({ ...u, runs: runSet.size })).sort((a, b) => b.costUsd - a.costUsd);
}

function health(entries: Entry[], latestRun: RunRow | undefined, now: string): Health {
  const starts = entries.filter((e) => e.phase === "start");
  const runState: Health["runState"] = latestRun?.state ?? "no runs yet";
  const since = new Date(Date.parse(now) - 86400_000).toISOString();
  return {
    lastActivity: entries.length ? entries[entries.length - 1].ts : null,
    currentRun: latestRun?.run ?? null,
    runState,
    runsToday: starts.filter((s) => day(s.ts) === day(now)).length,
    errors24h: entries.filter((e) => e.outcome === "error" && e.ts >= since),
  };
}

function repos(entries: Entry[]): RepoRow[] {
  const opened = entries.filter((e) => e.phase === "pr.opened");
  return latestPer(entries.filter((e) => e.phase === "policy"), (e) => e.subject)
    .map((e) => ({
      repo: e.subject,
      verdict: e.result,
      text: e.why.replace(/^(allow|ban|disclose):\s*/, ""),
      files: e.evidence,
      checked: e.ts,
      prs: opened.filter((o) => issueRepo(o.subject) === e.subject).length,
    }))
    .sort((a, b) => a.verdict.localeCompare(b.verdict) || a.repo.localeCompare(b.repo));
}

export function derive(ledger: Ledger): View {
  const sorted = [...ledger.decisions].sort((a, b) => a.ts.localeCompare(b.ts));
  const entries: Entry[] = sorted.map((d, i) => ({ ...d, id: `${d.run}-${i}`, outcome: outcomeOf(d), day: day(d.ts) }));
  // Sample data is frozen in time, so measure "now" from its last row.
  const latest = [entries.at(-1)?.ts, ledger.spend.at(-1)?.ts].filter(Boolean).sort().at(-1);
  const now = ledger.origin.kind === "sample" && latest ? latest : ledger.fetchedAt;
  const days = [...new Set(entries.map((e) => e.day))].sort().reverse();
  const stagesByDay = Object.fromEntries(days.map((d) => [d, stages(entries.filter((e) => e.day === d))]));
  const runRows = runs(entries, ledger.tokens, ledger.config, now);
  return {
    origin: ledger.origin,
    fetchedAt: ledger.fetchedAt,
    now,
    days,
    entries,
    stagesByDay,
    credits: credits(ledger.spend, now),
    history: history(ledger.spend, entries, now),
    runs: runRows,
    rejections: rejections(entries),
    models: models(ledger.tokens),
    tokensFromSample: ledger.origin.kind === "sample",
    health: health(entries, runRows[0], now),
    repos: repos(entries),
  };
}
