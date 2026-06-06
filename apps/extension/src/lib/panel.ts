export const panelHighlights = [
  "Detect visible form fields",
  "Fill trusted profile data",
  "Route sensitive answers to review",
  "Stop before final submit",
];

export const autofillSafetyNotes = [
  "No submission clicks are performed by the engine.",
  "Unknown fields stay in the review queue.",
  "Sensitive answers must come from trusted data only.",
];

export const getPanelStatusMessage = (site: string): string => {
  return `Ready to inspect ${site} and prepare autofill without bypassing security controls.`;
};

