import { getConfig } from "@/lib/config";

// Next.js calls register() once when the server starts. A bad .env.local must stop the app here,
// not on the first request: print the message (it names the variable) and exit.
export async function register(): Promise<void> {
  try {
    getConfig();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}
