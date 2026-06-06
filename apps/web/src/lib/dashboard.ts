export interface MetricCard {
  label: string;
  value: string;
  delta: string;
}

export const metricCards: MetricCard[] = [
  { label: "Jobs scored", value: "48", delta: "+12%" },
  { label: "Resumes tailored", value: "9", delta: "+3" },
  { label: "Applications prepared", value: "14", delta: "2 pending review" },
];

export const pipelineStages = [
  { label: "Discovery", count: 18 },
  { label: "Matched", count: 11 },
  { label: "Tailoring", count: 5 },
  { label: "Ready for review", count: 4 },
];
