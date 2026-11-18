import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ConfigError, getConfig } from "@/lib/config";
import { register } from "@/instrumentation";

const VALID = {
  REGISTRY_URL: "http://127.0.0.1:8000",
  WEATHER_URL: "http://127.0.0.1:8001",
  PLANNER_URL: "http://127.0.0.1:8002",
  REQUEST_TIMEOUT_MS: "3000",
};

function setEnv(overrides: Record<string, string | undefined> = {}) {
  for (const [name, value] of Object.entries({ ...VALID, ...overrides })) {
    if (value === undefined) vi.stubEnv(name, undefined as unknown as string);
    else vi.stubEnv(name, value);
  }
}

beforeEach(() => setEnv());
afterEach(() => vi.unstubAllEnvs());

describe("getConfig", () => {
  test("returns the four settings, with trailing slashes removed from the URLs", () => {
    setEnv({ REGISTRY_URL: "http://registry:8000/", PLANNER_URL: "https://planner.example//" });
    expect(getConfig()).toEqual({
      registryUrl: "http://registry:8000",
      weatherUrl: "http://127.0.0.1:8001",
      plannerUrl: "https://planner.example",
      requestTimeoutMs: 3000,
    });
  });

  test.each(Object.keys(VALID))("a missing %s throws a ConfigError naming it", (name) => {
    setEnv({ [name]: undefined });
    expect(() => getConfig()).toThrow(ConfigError);
    expect(() => getConfig()).toThrow(name);
  });

  test.each(["REGISTRY_URL", "WEATHER_URL", "PLANNER_URL"])(
    "%s that is not an http(s) URL throws naming it",
    (name) => {
      setEnv({ [name]: "127.0.0.1:8000" });
      expect(() => getConfig()).toThrow(name);
    },
  );

  test.each(["0", "-1", "abc", "NaN", "Infinity", "1.5", ""])(
    "REQUEST_TIMEOUT_MS=%j throws naming it",
    (value) => {
      setEnv({ REQUEST_TIMEOUT_MS: value });
      expect(() => getConfig()).toThrow("REQUEST_TIMEOUT_MS");
    },
  );
});

describe("register (runs when the server starts)", () => {
  test("a bad configuration prints the message naming the variable and exits the process", async () => {
    setEnv({ PLANNER_URL: undefined });
    const exit = vi.spyOn(process, "exit").mockImplementation((() => undefined) as never);
    const log = vi.spyOn(console, "error").mockImplementation(() => undefined);
    await register();
    expect(log).toHaveBeenCalledWith(expect.stringContaining("PLANNER_URL"));
    expect(exit).toHaveBeenCalledWith(1);
    exit.mockRestore();
    log.mockRestore();
  });

  test("does nothing when the configuration is valid", async () => {
    const exit = vi.spyOn(process, "exit").mockImplementation((() => undefined) as never);
    await expect(register()).resolves.toBeUndefined();
    expect(exit).not.toHaveBeenCalled();
    exit.mockRestore();
  });
});
