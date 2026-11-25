import type { ServiceStatus } from "@/lib/health";
import type { ServiceName } from "@/lib/types";

const SHORT: Record<ServiceName, string> = {
  "registry-service": "Registry",
  "weather-service": "Weather",
  "planner-service": "Planner",
};

// Up and down differ by shape and by word, not by colour alone. `null` means the check is still
// running.
export function StatusLineView({ statuses }: { statuses: ServiceStatus[] | null }) {
  return (
    <div role="status" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
      {statuses === null ? (
        <span className="text-muted-foreground">Checking services</span>
      ) : (
        statuses.map(({ service, up }) => (
          <span key={service} className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className={up ? "text-foreground" : "font-bold text-destructive"}>
              {up ? "●" : "✕"}
            </span>
            <span>{SHORT[service]}</span>
            <span className={up ? "text-muted-foreground" : "font-bold text-destructive"}>{up ? "up" : "down"}</span>
          </span>
        ))
      )}
    </div>
  );
}
