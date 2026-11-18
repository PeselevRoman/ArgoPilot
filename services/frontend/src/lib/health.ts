import { getConfig } from "@/lib/config";
import { getJson } from "@/lib/http";
import type { ServiceName } from "@/lib/types";

export type ServiceStatus = { service: ServiceName; up: boolean };

async function isUp(service: ServiceName, baseUrl: string): Promise<ServiceStatus> {
  const result = await getJson(service, `${baseUrl}/health`);
  // A 200 is not enough: the service must say {"status": "ok"}.
  const up =
    result.ok &&
    typeof result.data === "object" &&
    result.data !== null &&
    (result.data as { status?: unknown }).status === "ok";
  return { service, up };
}

// Always three entries, in a fixed order. It never throws: a service that fails is "down".
export async function checkHealth(): Promise<ServiceStatus[]> {
  const config = getConfig();
  return Promise.all([
    isUp("registry-service", config.registryUrl),
    isUp("weather-service", config.weatherUrl),
    isUp("planner-service", config.plannerUrl),
  ]);
}
