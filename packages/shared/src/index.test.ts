import { describe, expect, it } from "vitest";

import { createScopedKey } from "./index";

describe("createScopedKey", () => {
  it("namespaces keys by user and profile", () => {
    expect(
      createScopedKey({ userId: "user-1", profileId: "profile-abc" }, "resume"),
    ).toBe("user-1:profile-abc:resume");
  });
});
