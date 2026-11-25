import { connection } from "next/server";
import { StatusLineView } from "@/components/status-line-view";
import { checkHealth } from "@/lib/health";

// The async part of the status line: it asks the three /health endpoints. The layout wraps it in
// <Suspense>, so a slow service never delays the page: the page shows "Checking services" first.
export async function StatusLine() {
  // Wait for a real request: the health must be checked now, never at build time.
  await connection();
  return <StatusLineView statuses={await checkHealth()} />;
}
