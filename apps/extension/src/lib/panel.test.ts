import { describe, expect, it } from "vitest";

import { getPanelStatusMessage, panelHighlights } from "./panel";

describe("panel helpers", () => {
  it("describes supported site inspection safely", () => {
    expect(getPanelStatusMessage("LinkedIn")).toContain("LinkedIn");
  });

  it("exposes the key safety points", () => {
    expect(panelHighlights).toContain("Stop before final submit");
  });
});
