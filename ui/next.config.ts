import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The sample ledger is read from disk when LEDGER_BUCKET is not set.
  outputFileTracingIncludes: { "/": ["./lib/sample/**"] },
};

export default nextConfig;
