export type DashboardSectionKey =
  | "overview"
  | "profiles"
  | "jobs"
  | "resumes"
  | "approvals"
  | "agent";

export interface DashboardMetric {
  label: string;
  value: string;
  delta: string;
  helper: string;
}

export interface ProfileSummary {
  id: string;
  name: string;
  headline: string;
  location: string;
  focus: string;
  status: "active" | "paused" | "needs-review";
}

export interface JobSummary {
  id: string;
  title: string;
  company: string;
  source: string;
  match: number;
  stage: "discovered" | "analyzed" | "tailored" | "review";
}

export interface ResumeVersionSummary {
  id: string;
  title: string;
  jobTitle: string;
  atsScore: number;
  updatedAt: string;
  exportReady: boolean;
}

export interface ApprovalItem {
  id: string;
  title: string;
  detail: string;
  reason: string;
}

export interface AgentRunSummary {
  id: string;
  label: string;
  status: "running" | "paused" | "stopped";
  nextStep: string;
}

export interface DashboardSnapshot {
  activeProfileId: string;
  profile: ProfileSummary;
  metrics: DashboardMetric[];
  pipelineStages: { label: string; count: number }[];
  recentJobs: JobSummary[];
  resumeVersions: ResumeVersionSummary[];
  approvals: ApprovalItem[];
  agentRuns: AgentRunSummary[];
  profiles: ProfileSummary[];
}

export interface NavigationItem {
  label: string;
  href: string;
  description: string;
  section: DashboardSectionKey;
}

export const navigationItems: NavigationItem[] = [
  {
    label: "Command Center",
    href: "/",
    description: "Overview and live system status",
    section: "overview",
  },
  {
    label: "Profiles",
    href: "/profiles",
    description: "Switch between active candidate profiles",
    section: "profiles",
  },
  {
    label: "Jobs",
    href: "/jobs",
    description: "Track discovery, scoring, and tailoring",
    section: "jobs",
  },
  {
    label: "Resumes",
    href: "/resumes",
    description: "Review tailored resumes and exports",
    section: "resumes",
  },
  {
    label: "Approvals",
    href: "/approvals",
    description: "Approve sensitive answers before submission",
    section: "approvals",
  },
  {
    label: "Agent Runs",
    href: "/agent",
    description: "Continuous automation lifecycle",
    section: "agent",
  },
];

export const profiles: ProfileSummary[] = [
  {
    id: "product-engineer",
    name: "Product Engineer",
    headline: "Frontend-heavy full-stack candidate",
    location: "Austin, TX",
    focus: "React, platform UX, and product-minded engineering",
    status: "active",
  },
  {
    id: "backend-engineer",
    name: "Backend Engineer",
    headline: "API and automation specialist",
    location: "Remote",
    focus: "Python, FastAPI, scoring, and workflow systems",
    status: "paused",
  },
  {
    id: "data-ops",
    name: "Data Ops Lead",
    headline: "Operational analytics and reliability profile",
    location: "Chicago, IL",
    focus: "pipelines, observability, and internal tooling",
    status: "needs-review",
  },
];

export const metricsByProfile: Record<string, DashboardMetric[]> = {
  "product-engineer": [
    {
      label: "Jobs scored",
      value: "48",
      delta: "+12%",
      helper: "Directly matched against active profile criteria.",
    },
    {
      label: "Resumes tailored",
      value: "9",
      delta: "+3",
      helper: "Evidence-backed resume versions ready for export.",
    },
    {
      label: "Applications prepared",
      value: "14",
      delta: "2 pending review",
      helper: "Queued behind human approval gates.",
    },
  ],
  "backend-engineer": [
    {
      label: "Jobs scored",
      value: "31",
      delta: "+8%",
      helper: "High-confidence backend and infra targets.",
    },
    {
      label: "Resumes tailored",
      value: "7",
      delta: "+2",
      helper: "Versions exported for ATS-safe submission.",
    },
    {
      label: "Applications prepared",
      value: "8",
      delta: "1 pending review",
      helper: "Sensitive answers paused for verification.",
    },
  ],
  "data-ops": [
    {
      label: "Jobs scored",
      value: "22",
      delta: "+5%",
      helper: "Operational and analytics roles only.",
    },
    {
      label: "Resumes tailored",
      value: "5",
      delta: "+1",
      helper: "Candidate stories adapted per role.",
    },
    {
      label: "Applications prepared",
      value: "6",
      delta: "3 pending review",
      helper: "Approval-first workflow remains active.",
    },
  ],
};

export const pipelineStagesByProfile: Record<
  string,
  { label: string; count: number }[]
> = {
  "product-engineer": [
    { label: "Discovery", count: 18 },
    { label: "Matched", count: 11 },
    { label: "Tailoring", count: 5 },
    { label: "Ready for review", count: 4 },
  ],
  "backend-engineer": [
    { label: "Discovery", count: 12 },
    { label: "Matched", count: 8 },
    { label: "Tailoring", count: 4 },
    { label: "Ready for review", count: 2 },
  ],
  "data-ops": [
    { label: "Discovery", count: 9 },
    { label: "Matched", count: 6 },
    { label: "Tailoring", count: 3 },
    { label: "Ready for review", count: 3 },
  ],
};

export const jobsByProfile: Record<string, JobSummary[]> = {
  "product-engineer": [
    {
      id: "job-1",
      title: "Senior Product Engineer",
      company: "Ashby",
      source: "Greenhouse",
      match: 94,
      stage: "tailored",
    },
    {
      id: "job-2",
      title: "Frontend Engineer",
      company: "Linear",
      source: "Lever",
      match: 91,
      stage: "analyzed",
    },
    {
      id: "job-3",
      title: "Platform Engineer",
      company: "Vercel",
      source: "Custom",
      match: 86,
      stage: "review",
    },
  ],
  "backend-engineer": [
    {
      id: "job-4",
      title: "Senior Backend Engineer",
      company: "Acme",
      source: "Greenhouse",
      match: 96,
      stage: "tailored",
    },
    {
      id: "job-5",
      title: "API Engineer",
      company: "Pilot",
      source: "Ashby",
      match: 89,
      stage: "analyzed",
    },
    {
      id: "job-6",
      title: "Infrastructure Engineer",
      company: "Figma",
      source: "Lever",
      match: 84,
      stage: "review",
    },
  ],
  "data-ops": [
    {
      id: "job-7",
      title: "Data Platform Engineer",
      company: "Mode",
      source: "Greenhouse",
      match: 92,
      stage: "tailored",
    },
    {
      id: "job-8",
      title: "Ops Analytics Engineer",
      company: "Notion",
      source: "Lever",
      match: 88,
      stage: "analyzed",
    },
    {
      id: "job-9",
      title: "Workflow Reliability Lead",
      company: "Airtable",
      source: "Custom",
      match: 83,
      stage: "review",
    },
  ],
};

export const resumeVersionsByProfile: Record<string, ResumeVersionSummary[]> = {
  "product-engineer": [
    {
      id: "rv-1",
      title: "Product Engineer v9",
      jobTitle: "Senior Product Engineer",
      atsScore: 92,
      updatedAt: "2 minutes ago",
      exportReady: true,
    },
    {
      id: "rv-2",
      title: "Product Engineer v8",
      jobTitle: "Frontend Engineer",
      atsScore: 88,
      updatedAt: "18 minutes ago",
      exportReady: true,
    },
  ],
  "backend-engineer": [
    {
      id: "rv-3",
      title: "Backend Engineer v7",
      jobTitle: "Senior Backend Engineer",
      atsScore: 95,
      updatedAt: "5 minutes ago",
      exportReady: true,
    },
    {
      id: "rv-4",
      title: "Backend Engineer v6",
      jobTitle: "API Engineer",
      atsScore: 89,
      updatedAt: "39 minutes ago",
      exportReady: true,
    },
  ],
  "data-ops": [
    {
      id: "rv-5",
      title: "Data Ops v5",
      jobTitle: "Data Platform Engineer",
      atsScore: 91,
      updatedAt: "9 minutes ago",
      exportReady: true,
    },
    {
      id: "rv-6",
      title: "Data Ops v4",
      jobTitle: "Ops Analytics Engineer",
      atsScore: 86,
      updatedAt: "1 hour ago",
      exportReady: false,
    },
  ],
};

export const approvalsByProfile: Record<string, ApprovalItem[]> = {
  "product-engineer": [
    {
      id: "approval-1",
      title: "Location question",
      detail: "Role asks for relocation flexibility.",
      reason: "Needs approval before answering with a broad yes.",
    },
    {
      id: "approval-2",
      title: "Salary expectation",
      detail: "Compensation field appears mandatory.",
      reason: "Use trusted profile data only after review.",
    },
  ],
  "backend-engineer": [
    {
      id: "approval-3",
      title: "Work authorization",
      detail: "Application asks for US work authorization.",
      reason: "Confirm exact wording before autofill.",
    },
  ],
  "data-ops": [
    {
      id: "approval-4",
      title: "Start date",
      detail: "Role expects availability within two weeks.",
      reason: "Human check required before finalizing.",
    },
  ],
};

export const agentRunsByProfile: Record<string, AgentRunSummary[]> = {
  "product-engineer": [
    {
      id: "run-1",
      label: "Nightly discovery sweep",
      status: "running",
      nextStep: "Score new jobs after connectors finish.",
    },
    {
      id: "run-2",
      label: "Resume tuning session",
      status: "paused",
      nextStep: "Wait for ATS validation on the latest version.",
    },
  ],
  "backend-engineer": [
    {
      id: "run-3",
      label: "Backend keyword scan",
      status: "running",
      nextStep: "Tailor the next matched role.",
    },
    {
      id: "run-4",
      label: "Follow-up queue",
      status: "stopped",
      nextStep: "Resume once approval center clears responses.",
    },
  ],
  "data-ops": [
    {
      id: "run-5",
      label: "Ops role crawler",
      status: "running",
      nextStep: "Refresh job matches from public sources.",
    },
  ],
};

export function resolveActiveProfileId(input?: string | null): string {
  const normalized = input?.trim();
  if (!normalized) {
    return profiles[0]?.id ?? "";
  }

  return profiles.some((profile) => profile.id === normalized)
    ? normalized
    : profiles[0]?.id ?? "";
}

export function getActiveProfile(profileId?: string | null): ProfileSummary {
  const resolvedId = resolveActiveProfileId(profileId);
  return profiles.find((profile) => profile.id === resolvedId) ?? profiles[0];
}

export function getDashboardSnapshot(profileId?: string | null): DashboardSnapshot {
  const profile = getActiveProfile(profileId);
  const resolvedId = profile.id;

  return {
    activeProfileId: resolvedId,
    profile,
    metrics: metricsByProfile[resolvedId] ?? metricsByProfile[profiles[0].id],
    pipelineStages:
      pipelineStagesByProfile[resolvedId] ??
      pipelineStagesByProfile[profiles[0].id],
    recentJobs: jobsByProfile[resolvedId] ?? jobsByProfile[profiles[0].id],
    resumeVersions:
      resumeVersionsByProfile[resolvedId] ??
      resumeVersionsByProfile[profiles[0].id],
    approvals: approvalsByProfile[resolvedId] ?? approvalsByProfile[profiles[0].id],
    agentRuns: agentRunsByProfile[resolvedId] ?? agentRunsByProfile[profiles[0].id],
    profiles,
  };
}

export function getNavigationHref(path: string, profileId: string): string {
  const searchParams = new URLSearchParams();
  searchParams.set("profile", profileId);
  return `${path}?${searchParams.toString()}`;
}

export function formatPercent(value: number): string {
  return `${value}%`;
}
