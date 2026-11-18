import type { ServiceError, ServiceName } from "@/lib/types";

export type ErrorMessage = { title: string; detail: string };

const NAMES: Record<ServiceName, string> = {
  "registry-service": "the registry",
  "weather-service": "the weather service",
  "planner-service": "the planner",
};

const capitalise = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
const RETRY = "Try again in a few minutes.";

// The planner's `detail` names the failing service ("weather-service is unavailable: ..."). We
// only read which service it names, and never show the detail itself: it can hold technical text.
function namedUpstreams(detail: string | undefined): ServiceName[] {
  const known: ServiceName[] = ["registry-service", "weather-service"];
  return known.filter((name) => detail?.includes(name));
}

// Turns a service failure into a short message for the grower: what happened and what to do.
export function describeError(error: ServiceError): ErrorMessage {
  const who = NAMES[error.service];

  if (error.kind === "unreachable") {
    return { title: `${capitalise(who)} is not available`, detail: RETRY };
  }
  if (error.kind === "timeout") {
    return { title: `${capitalise(who)} took too long to answer`, detail: RETRY };
  }
  if (error.kind === "bad-answer") {
    return {
      title: `${capitalise(who)} sent an answer this app cannot use`,
      detail: "No plan is shown, because it could not be trusted. " + RETRY,
    };
  }

  if (error.status === 404 && error.code === "NOT_FOUND") {
    return { title: "This plot does not exist", detail: "Check the link, or go back to the list of plots." };
  }
  if (error.code === "UPSTREAM_UNAVAILABLE") {
    const named = namedUpstreams(error.detail);
    if (named.length === 0) {
      return {
        title: "A service the planner needs is not available",
        detail: "The plan cannot be built without it. " + RETRY,
      };
    }
    const title = capitalise(named.map((name) => NAMES[name]).join(" or "));
    return {
      title: `${title} is not available`,
      detail: `The planner needs ${named.length === 1 ? "it" : "them"} to build the plan. ${RETRY}`,
    };
  }
  return {
    title: "The plan is not available right now",
    detail: `${capitalise(who)} reported a problem. ${RETRY}`,
  };
}
