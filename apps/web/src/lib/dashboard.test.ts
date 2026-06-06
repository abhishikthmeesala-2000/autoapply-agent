import { describe, expect, it } from "vitest";

import { metricCards, pipelineStages } from "./dashboard";

describe("dashboard data", () => {
  it("exposes the expected number of metric cards", () => {
    expect(metricCards).toHaveLength(3);
  });

  it("includes pipeline stages for the shell", () => {
    expect(pipelineStages[0]?.label).toBe("Discovery");
  });
});
