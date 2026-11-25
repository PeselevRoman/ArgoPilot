import { expect, test } from "vitest";
import { decodePlotId } from "@/lib/plot-id";

// Next.js hands the page the id still percent-encoded; the clients encode it again, so the page
// must decode it once first (otherwise "a b" would be asked for as "a%2520b").
test.each([
  ["abc", "abc"],
  ["a%20b", "a b"],
  ["..%2Fhealth", "../health"],
  ["x%3Fy%3D1", "x?y=1"],
])("decodePlotId(%s) is %s", (raw, id) => {
  expect(decodePlotId(raw)).toBe(id);
});

test("an id that is not valid percent-encoding is null, not an exception", () => {
  expect(decodePlotId("%E0%A4%A")).toBeNull();
  expect(decodePlotId("%")).toBeNull();
});
