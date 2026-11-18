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

// What the frontend shows. camelCase here, snake_case in the services' JSON (parse.ts converts).
export type Farm = { id: string; name: string };
export type Plot = { id: string; farmId: string; name: string; cropId: string; areaM2: number };
export type FarmWithPlots = { farm: Farm; plots: Plot[] };

export type PlanDay = {
  date: string; // YYYY-MM-DD
  et0Mm: number;
  kc: number;
  litres: number;
  runMinutes: number;
  stale: boolean;
  bucketMm: number;
};
export type Plan = { plotId: string; days: PlanDay[] };
