import { Dashboard } from "@/components/dashboard";
import { derive } from "@/lib/derive";
import { loadLedger } from "@/lib/ledger";

// The host mirrors the ledger to the dataset every 30 minutes; re-reading every 5 is plenty.
export const revalidate = 300;

export default async function Page() {
  const view = derive(await loadLedger());
  return <Dashboard view={view} />;
}
