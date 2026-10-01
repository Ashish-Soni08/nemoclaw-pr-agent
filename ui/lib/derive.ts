import type { Decision, Ledger, Spend } from "./ledger";

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
  fromProvider: boolean;
  source: string;
  daily: { day: string; amount: number }[];
  runsOut: string;
  asOf: string;
};

export type Health = {
  lastActivity: string | null;
  currentRun: string | null;
  runState: "running" | "finished" | "stopped by budget" | "no runs yet";
  runsToday: number;
  errors24h: Entry[];
};

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
  const fixesStarted = new Set(rows.filter((r) => r.phase.startsWith("fix.")).map((r) => r.subject));
  const abandoned = by("fix.abandoned");
  const opened = by("pr.opened");
  const refused = by("pr.refused");
  return [
    { key: "found", label: "Issues checked", count: verify.length, note: verify.length ? `${verify.length - kept.length} dropped${dropReasons ? ` · ${dropReasons}` : ""}` : "no discovery", phases: ["discover.query", "discover.verify", "discover.seen", "discover.precedent", "discover.summary"] },
    { key: "kept", label: "Still open", count: kept.length, note: "unassigned, no open PR", phases: ["discover.verify"] },
    { key: "policy", label: "Repos allow AI", count: allowed.length, note: notAllowed || `of ${policy.length} repos checked`, phases: ["policy"] },
    { key: "triage", label: "Chosen", count: takes.length, note: `${skips.length} skipped in triage`, phases: ["triage"] },
    { key: "work", label: "Worked on", count: fixesStarted.size + claims.length, note: `${claims.length} claim${claims.length === 1 ? "" : "s"} waiting · ${abandoned.length} abandoned`, phases: ["claim.posted", "claim.status", "fix.workspace", "fix.setup", "fix.test.baseline", "fix.test.after", "fix.abandoned", "gate"] },
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
    // A drop means the running total was reset (new month); the new total is that day's spend.
    return { day: d, amount: cur >= prev ? cur - prev : cur };
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
  const first = [spend[0]?.ts, entries[0]?.ts].filter(Boolean).map((t) => day(t!)).sort()[0];
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

function health(entries: Entry[], now: string): Health {
  const starts = entries.filter((e) => e.phase === "start");
  const lastStart = starts[starts.length - 1];
  let runState: Health["runState"] = "no runs yet";
  if (lastStart) {
    const runRows = entries.filter((e) => e.run === lastStart.run);
    if (runRows.some((e) => e.phase === "guard" && e.result === "skipped")) runState = "stopped by budget";
    else if (runRows.some((e) => e.phase === "run.end")) runState = "finished";
    else runState = "running";
  }
  const since = new Date(Date.parse(now) - 86400_000).toISOString();
  return {
    lastActivity: entries.length ? entries[entries.length - 1].ts : null,
    currentRun: lastStart?.run ?? null,
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
  return {
    origin: ledger.origin,
    fetchedAt: ledger.fetchedAt,
    now,
    days,
    entries,
    stagesByDay,
    credits: credits(ledger.spend, now),
    history: history(ledger.spend, entries, now),
    health: health(entries, now),
    repos: repos(entries),
  };
}
