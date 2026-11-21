// Next.js calls register() once when the server starts. A bad .env.local must stop the app here,
// not on the first request. The check lives in its own file and is loaded only for the Node.js
// runtime, because it uses process.exit.
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { checkConfigOrExit } = await import("@/instrumentation-node");
    checkConfigOrExit();
  }
}
