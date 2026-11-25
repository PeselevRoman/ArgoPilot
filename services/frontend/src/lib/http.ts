import { getConfig } from "@/lib/config";
import type { Result, ServiceError, ServiceName } from "@/lib/types";

function fail(error: ServiceError): Result<never> {
  return { ok: false, error };
}

function text(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

// GET a URL and return its JSON. It never throws for a service failure: every way a call can
// go wrong becomes a typed error, so the page can always say what happened.
export async function getJson(service: ServiceName, url: string): Promise<Result<unknown>> {
  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(getConfig().requestTimeoutMs),
    });
  } catch (error) {
    // AbortSignal.timeout aborts with a DOMException named "TimeoutError". Match on the name,
    // not on instanceof: the exception can come from another realm (for example under jsdom).
    const timedOut = (error as { name?: unknown } | null)?.name === "TimeoutError";
    return fail({ service, kind: timedOut ? "timeout" : "unreachable" });
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }

  if (!response.ok) {
    const problem = typeof body === "object" && body !== null ? (body as Record<string, unknown>) : {};
    const error: ServiceError = { service, kind: "problem", status: response.status };
    const code = text(problem.code);
    const detail = text(problem.detail);
    if (code !== undefined) error.code = code;
    if (detail !== undefined) error.detail = detail;
    return fail(error);
  }
  if (body === undefined) return fail({ service, kind: "bad-answer" });
  return { ok: true, data: body };
}
