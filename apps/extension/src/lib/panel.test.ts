import { describe, expect, it } from "vitest";

import {
  autofillSafetyNotes,
  getPanelStatusMessage,
  panelHighlights,
} from "./panel";

describe("panel helpers", () => {
  it("describes supported site inspection safely", () => {
    expect(getPanelStatusMessage("LinkedIn")).toContain("LinkedIn");
  });

  it("exposes the key safety points", () => {
    expect(panelHighlights).toContain("Fill trusted profile data");
    expect(autofillSafetyNotes).toContain("No submission clicks are performed by the engine.");
  });
});
