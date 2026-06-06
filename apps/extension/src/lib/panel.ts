export const panelHighlights = [
  "Extract visible job details",
  "Support safe autofill",
  "Stop before final submit",
];

export const getPanelStatusMessage = (site: string): string => {
  return `Ready to inspect ${site} without bypassing security controls.`;
};
