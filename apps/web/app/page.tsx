import {
  ArrowUpRight,
  CheckCircle2,
  CircleAlert,
  Download,
  FileBadge2,
  MailQuestion,
  Target,
} from "lucide-react";

import { DashboardShell } from "../src/components/dashboard-shell";
import { getApiBaseUrl } from "../src/lib/api";
import { getDashboardSnapshot, resolveActiveProfileId } from "../src/lib/dashboard";

interface HomePageProps {
  searchParams?: {
    profile?: string;
  };
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const activeProfileId = resolveActiveProfileId(searchParams?.profile);
  const snapshot = getDashboardSnapshot(activeProfileId);

  return (
    <DashboardShell
      activeProfile={snapshot.profile}
      activeSection="overview"
      profiles={snapshot.profiles}
      currentPath="/"
    >
      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <section className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            {snapshot.metrics.map((metric) => (
              <article
                key={metric.label}
                className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-5 shadow-glow"
              >
                <p className="text-sm text-slate-400">{metric.label}</p>
                <div className="mt-4 flex items-end justify-between gap-4">
                  <p className="text-4xl font-semibold text-white">{metric.value}</p>
                  <span className="inline-flex items-center gap-1 rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-300">
                    {metric.delta}
                    <ArrowUpRight className="h-3 w-3" />
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  {metric.helper}
                </p>
              </article>
            ))}
          </div>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-semibold text-white">
                  Application pipeline
                </h3>
                <p className="mt-1 text-sm text-slate-400">
                  The workflow keeps discovery, scoring, tailoring, and review
                  visibly separated.
                </p>
              </div>
              <Target className="h-5 w-5 text-slate-400" />
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-4">
              {snapshot.pipelineStages.map((stage) => (
                <div
                  key={stage.label}
                  className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                >
                  <p className="text-sm text-slate-400">{stage.label}</p>
                  <p className="mt-2 text-3xl font-semibold text-white">
                    {stage.count}
                  </p>
                </div>
              ))}
            </div>
          </article>

          <div className="grid gap-6 lg:grid-cols-2">
            <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-xl font-semibold text-white">
                    Latest jobs
                  </h3>
                  <p className="mt-1 text-sm text-slate-400">
                    Mock data mirrors the backend contract and keeps the
                    dashboard useful without a live service.
                  </p>
                </div>
                <FileBadge2 className="h-5 w-5 text-slate-400" />
              </div>

              <div className="mt-5 space-y-3">
                {snapshot.recentJobs.map((job) => (
                  <div
                    key={job.id}
                    className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-white">{job.title}</p>
                        <p className="mt-1 text-sm text-slate-400">
                          {job.company} • {job.source}
                        </p>
                      </div>
                      <span className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-xs font-medium text-cyan-300">
                        {job.match}% match
                      </span>
                    </div>
                    <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                      Stage: {job.stage}
                    </p>
                  </div>
                ))}
              </div>
            </article>

            <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
              <h3 className="text-xl font-semibold text-white">
                API connection
              </h3>
              <div className="mt-4 rounded-2xl border border-slate-800 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Base URL</p>
                <p className="mt-1 break-all font-mono text-sm text-white">
                  {getApiBaseUrl()}
                </p>
                <div className="mt-4 flex items-center gap-2">
                  <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
                  <p className="text-sm font-medium text-white">Health check wired</p>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  The dashboard calls `/health` first and falls back to mocked
                  records if the backend is offline.
                </p>
              </div>

              <div className="mt-5 space-y-3">
                {[
                  "/profiles/{profile_id}/resume/master",
                  "/profiles/{profile_id}/resume/evidence",
                  "/profiles/{profile_id}/resume_versions/{id}/export",
                ].map((endpoint) => (
                  <div
                    key={endpoint}
                    className="rounded-2xl border border-slate-800 bg-white/5 p-4 font-mono text-xs text-slate-300"
                  >
                    {endpoint}
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>

        <aside className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                  Active profile
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-white">
                  {snapshot.profile.name}
                </h3>
              </div>
              <CheckCircle2 className="h-5 w-5 text-emerald-300" />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              {snapshot.profile.headline}
            </p>
            <dl className="mt-5 space-y-3 text-sm">
              <div className="flex items-center justify-between gap-4">
                <dt className="text-slate-500">Location</dt>
                <dd className="text-white">{snapshot.profile.location}</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-slate-500">Focus</dt>
                <dd className="max-w-[18rem] text-right text-white">
                  {snapshot.profile.focus}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-slate-500">Status</dt>
                <dd className="text-cyan-300">{snapshot.profile.status}</dd>
              </div>
            </dl>
          </article>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <h3 className="text-xl font-semibold text-white">
              Recent approvals
            </h3>
            <div className="mt-5 space-y-3">
              {snapshot.approvals.map((approval) => (
                <div
                  key={approval.id}
                  className="rounded-2xl border border-amber-500/20 bg-amber-500/8 p-4"
                >
                  <div className="flex items-center gap-2 text-amber-200">
                    <CircleAlert className="h-4 w-4" />
                    <p className="font-medium">{approval.title}</p>
                  </div>
                  <p className="mt-2 text-sm text-slate-300">{approval.detail}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    {approval.reason}
                  </p>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-cyan-300">
              <Download className="h-4 w-4" />
              <h3 className="text-xl font-semibold text-white">
                Ready exports
              </h3>
            </div>
            <div className="mt-4 space-y-3">
              {snapshot.resumeVersions.map((resumeVersion) => (
                <div
                  key={resumeVersion.id}
                  className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-white">{resumeVersion.title}</p>
                    <span className="text-xs text-slate-500">
                      ATS {resumeVersion.atsScore}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-400">
                    {resumeVersion.jobTitle}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                    Updated {resumeVersion.updatedAt}
                  </p>
                </div>
              ))}
            </div>
          </article>
        </aside>
      </div>
    </DashboardShell>
  );
}

