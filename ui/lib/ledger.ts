import { readFile } from "node:fs/promises";
import path from "node:path";

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

export type Ledger = {
  decisions: Decision[];
  spend: Spend[];
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

async function fromDataset(dataset: string, file: string): Promise<string> {
  // The dataset is private, so the read token stays on the server.
  const headers: Record<string, string> = {};
  if (process.env.HF_TOKEN) headers.Authorization = `Bearer ${process.env.HF_TOKEN}`;
  const res = await fetch(`${HUB}/datasets/${dataset}/resolve/main/ledger/${file}`, {
    headers,
    next: { revalidate: 300 },
  });
  if (res.status === 404) return "";
  if (!res.ok) throw new Error(`Could not read ledger/${file} from dataset ${dataset}: HTTP ${res.status}`);
  return res.text();
}

async function fromSample(file: string): Promise<string> {
  return readFile(path.join(process.cwd(), "lib", "sample", file), "utf8");
}

export async function loadLedger(): Promise<Ledger> {
  const dataset = process.env.LEDGER_DATASET?.replace(/^datasets\//, "").replace(/\/+$/, "");
  const read = dataset ? (f: string) => fromDataset(dataset, f) : fromSample;
  const [d, s] = await Promise.all([read("decisions.tsv"), read("spend.tsv")]);
  return {
    decisions: toDecisions(d),
    spend: toSpend(s),
    origin: dataset ? { kind: "dataset", dataset } : { kind: "sample" },
    fetchedAt: new Date().toISOString(),
  };
}
