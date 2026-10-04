import { SAMPLE } from "./sample";

// Shapes written by the agent (src/pr_agent/ledger.py and spend.py).
export type Decision = {
  ts: string;
  run: string;
  phase: string;
  subject: string;
  decision: string;
  why: string;
  evidence: string;
  result: string;
};

export type Spend = {
  ts: string;
  provider: string;
  used: number;
  unit: string;
  cost_usd: number;
  remaining: number | null;
  limit: number | null;
  source: string;
};

// tokens.tsv: one row per model per step (per issue where there is one) per run.
// Proposed to the agent; not written by it yet.
export type TokenRow = {
  ts: string;
  run: string;
  subject: string;
  step: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
};

// run_config.tsv: the settings each run started with, one key per row. Also proposed.
export type ConfigRow = { run: string; key: string; value: string };

// host.tsv: one VM sample a minute from a host-side sampler; empty cells when a number isn't available.
export type HostRow = {
  ts: string;
  run: string;
  cpu_pct: number | null;
  load1: number | null;
  ram_used_gb: number | null;
  ram_total_gb: number | null;
  gpu_util_pct: number | null;
  vram_used_gb: number | null;
  vram_total_gb: number | null;
  disk_used_gb: number | null;
  disk_total_gb: number | null;
  agent_cpu_cores: number | null;
  agent_ram_gb: number | null;
  agent_vram_gb: number | null;
  agent_disk_gb: number | null;
};

const HOST_NUMBERS = [
  "cpu_pct", "load1", "ram_used_gb", "ram_total_gb", "gpu_util_pct", "vram_used_gb", "vram_total_gb",
  "disk_used_gb", "disk_total_gb", "agent_cpu_cores", "agent_ram_gb", "agent_vram_gb", "agent_disk_gb",
] as const;

export type Ledger = {
  decisions: Decision[];
  spend: Spend[];
  tokens: TokenRow[];
  config: ConfigRow[];
  host: HostRow[];
  origin: { kind: "dataset"; dataset: string } | { kind: "sample" };
  fetchedAt: string;
};

const HUB = process.env.HF_ENDPOINT ?? "https://huggingface.co";

export function parseTsv(text: string): Record<string, string>[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length === 0) return [];
  const header = lines[0].split("\t");
  return lines.slice(1).map((line) => {
    const cells = line.split("\t");
    return Object.fromEntries(header.map((h, i) => [h, cells[i] ?? ""]));
  });
}

// ledger.py quotes a leading = + - @ so spreadsheets never run it; undo that for display.
const unquote = (v: string) => (/^'[=+\-@]/.test(v) ? v.slice(1) : v);
const num = (v: string) => (v === "" ? null : Number(v));

function toDecisions(text: string): Decision[] {
  return parseTsv(text).map((r) => ({
    ts: r.ts,
    run: r.run,
    phase: r.phase,
    subject: unquote(r.subject),
    decision: unquote(r.decision),
    why: unquote(r.why),
    evidence: unquote(r.evidence),
    result: unquote(r.result),
  }));
}

function toSpend(text: string): Spend[] {
  return parseTsv(text).map((r) => ({
    ts: r.ts,
    provider: r.provider,
    used: num(r.used) ?? 0,
    unit: r.unit,
    cost_usd: num(r.cost_usd) ?? 0,
    remaining: num(r.remaining),
    limit: num(r.limit),
    source: r.source,
  }));
}

function toTokens(text: string): TokenRow[] {
  return parseTsv(text).map((r) => ({
    ts: r.ts,
    run: r.run,
    subject: unquote(r.subject) || "-",
    step: unquote(r.step) || "-",
    model: unquote(r.model),
    tokens_in: num(r.tokens_in) ?? 0,
    tokens_out: num(r.tokens_out) ?? 0,
    cost_usd: num(r.cost_usd) ?? 0,
  }));
}

function toHost(text: string): HostRow[] {
  return parseTsv(text).map((r) => ({
    ts: r.ts,
    run: unquote(r.run) || "-",
    ...(Object.fromEntries(HOST_NUMBERS.map((k) => [k, num(r[k] ?? "")])) as Record<(typeof HOST_NUMBERS)[number], number | null>),
  }));
}

// A 404 on these means a wrong dataset name or a token that can't see it, not an empty
// ledger, so it fails the render and the last good page stays up.
const REQUIRED = new Set(["decisions.tsv", "spend.tsv"]);

async function fromDataset(dataset: string, file: string): Promise<string> {
  // The dataset is private, so the read token stays on the server.
  const headers: Record<string, string> = {};
  if (process.env.HF_TOKEN) headers.Authorization = `Bearer ${process.env.HF_TOKEN}`;
  const res = await fetch(`${HUB}/datasets/${dataset}/resolve/main/ledger/${file}`, {
    headers,
    next: { revalidate: 300 },
  });
  if (res.status === 404 && !REQUIRED.has(file)) return "";
  if (!res.ok) throw new Error(`Could not read ledger/${file} from dataset ${dataset}: HTTP ${res.status}`);
  return res.text();
}

async function fromSample(file: string): Promise<string> {
  return SAMPLE[file] ?? "";
}

export async function loadLedger(): Promise<Ledger> {
  const dataset = process.env.LEDGER_DATASET?.replace(/^datasets\//, "").replace(/\/+$/, "");
  const read = dataset ? (f: string) => fromDataset(dataset, f) : fromSample;
  const [d, s, t, c, h] = await Promise.all(["decisions.tsv", "spend.tsv", "tokens.tsv", "run_config.tsv", "host.tsv"].map(read));
  return {
    decisions: toDecisions(d),
    spend: toSpend(s),
    tokens: toTokens(t),
    config: parseTsv(c).map((r) => ({ run: r.run, key: r.key, value: unquote(r.value) })),
    host: toHost(h),
    origin: dataset ? { kind: "dataset", dataset } : { kind: "sample" },
    fetchedAt: new Date().toISOString(),
  };
}
