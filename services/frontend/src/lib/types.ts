// Shared types. Farm, Plot and Plan types are added with the clients that produce them.

export type ServiceName = "registry-service" | "weather-service" | "planner-service";

// Why a call to a service did not give a usable answer.
export type ServiceError = {
  service: ServiceName;
  kind: "unreachable" | "timeout" | "bad-answer" | "problem";
  status?: number; // HTTP status, for kind "problem"
  code?: string; // problem+json `code`
  detail?: string; // problem+json `detail`
};

// Like a C# result type: either the data, or the error, never a thrown exception.
export type Result<T> = { ok: true; data: T } | { ok: false; error: ServiceError };
