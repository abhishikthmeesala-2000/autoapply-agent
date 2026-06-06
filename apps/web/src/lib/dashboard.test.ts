import { describe, expect, it } from "vitest";

import {
  getActiveProfile,
  getDashboardSnapshot,
  getNavigationHref,
  navigationItems,
  resolveActiveProfileId,
} from "./dashboard";

describe("dashboard data", () => {
  it("resolves a safe default profile id when the input is unknown", () => {
    expect(resolveActiveProfileId("does-not-exist")).toBe("product-engineer");
  });

  it("returns the matching profile snapshot", () => {
    const snapshot = getDashboardSnapshot("backend-engineer");

    expect(snapshot.profile.id).toBe("backend-engineer");
    expect(snapshot.metrics).toHaveLength(3);
    expect(snapshot.recentJobs[0]?.company).toBe("Acme");
  });

  it("builds profile-aware navigation hrefs", () => {
    expect(getNavigationHref("/jobs", "data-ops")).toBe("/jobs?profile=data-ops");
  });

  it("keeps the main navigation consistent", () => {
    expect(navigationItems).toHaveLength(6);
    expect(navigationItems[0]?.label).toBe("Command Center");
  });

  it("returns the active profile record", () => {
    expect(getActiveProfile("data-ops").headline).toContain("Operational");
  });
});

