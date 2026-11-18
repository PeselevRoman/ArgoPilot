// Settings come from the environment (.env.local in development). There are no defaults in code:
// a missing or invalid value is a ConfigError that names the variable.

export type Config = {
  registryUrl: string;
  weatherUrl: string;
  plannerUrl: string;
  requestTimeoutMs: number;
};

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

function readUrl(name: string): string {
  const value = process.env[name];
  if (value === undefined || value.trim() === "") {
    throw new ConfigError(`${name} is missing. Set it in .env.local (see .env.example).`);
  }
  if (!/^https?:\/\//.test(value)) {
    throw new ConfigError(`${name} must start with http:// or https://`);
  }
  return value.replace(/\/+$/, "");
}

function readTimeout(name: string): number {
  const value = process.env[name];
  if (value === undefined || value.trim() === "") {
    throw new ConfigError(`${name} is missing. Set it in .env.local (see .env.example).`);
  }
  // Only plain digits: this refuses "1.5", "NaN", "Infinity" and "-1" in one check.
  if (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value)) || Number(value) <= 0) {
    throw new ConfigError(`${name} must be a whole number of milliseconds above 0`);
  }
  return Number(value);
}

// Read on every call, so a test can change the environment. It is cheap.
export function getConfig(): Config {
  return {
    registryUrl: readUrl("REGISTRY_URL"),
    weatherUrl: readUrl("WEATHER_URL"),
    plannerUrl: readUrl("PLANNER_URL"),
    requestTimeoutMs: readTimeout("REQUEST_TIMEOUT_MS"),
  };
}
