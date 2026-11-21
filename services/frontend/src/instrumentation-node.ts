import { getConfig } from "@/lib/config";

// Check the configuration, and stop the process with the message if it is bad. This file is only
// loaded in the Node.js runtime: process.exit does not exist in the Edge runtime.
export function checkConfigOrExit(): void {
  try {
    getConfig();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}
