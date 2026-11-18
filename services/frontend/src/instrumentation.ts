import { getConfig } from "@/lib/config";

// Next.js calls register() once when the server starts. Checking the configuration here
// means a bad .env.local stops the app at start, not on the first request.
export async function register(): Promise<void> {
  getConfig();
}
