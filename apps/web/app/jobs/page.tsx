import { BarChart3, CheckCircle2, Search, Sparkles } from "lucide-react";

import { DashboardShell } from "../../src/components/dashboard-shell";
import { getDashboardSnapshot, resolveActiveProfileId } from "../../src/lib/dashboard";

interface JobsPageProps {
  searchParams?: {
    profile?: string;
  };
}

export default async function JobsPage({ searchParams }: JobsPageProps) {
  const snapshot = getDashboardSnapshot(resolveActiveProfileId(searchParams?.profile));

  return (
    <DashboardShell
      activeProfile={snapshot.profile}
      activeSection="jobs"
      profiles={snapshot.profiles}
      currentPath="/jobs"
    >
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-semibold text-white">Job scoring pipeline</h3>
                <p className="mt-1 text-sm text-slate-400">
                  Discovery and scoring stay separate so the user can inspect every stage.
                </p>
              </div>
              <BarChart3 className="h-5 w-5 text-slate-400" />
            </div>
            <div className="mt-6 grid gap-3 md:grid-cols-4">
              {snapshot.pipelineStages.map((stage) => (
                <div
                  key={stage.label}
                  className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                >
                  <p className="text-sm text-slate-400">{stage.label}</p>
                  <p className="mt-2 text-3xl font-semibold text-white">{stage.count}</p>
                </div>
              ))}
            </div>
          </article>

          <div className="grid gap-4 md:grid-cols-2">
            {snapshot.recentJobs.map((job) => (
              <article
                key={job.id}
                className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-5 shadow-glow"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-lg font-semibold text-white">{job.title}</h4>
                    <p className="mt-1 text-sm text-slate-400">
                      {job.company} • {job.source}
                    </p>
                  </div>
                  <span className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-xs font-medium text-cyan-300">
                    {job.match}%
                  </span>
                </div>
                <div className="mt-4 flex items-center gap-2 text-sm text-slate-300">
                  <Search className="h-4 w-4 text-slate-500" />
                  Stage: {job.stage}
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-emerald-300">
              <Sparkles className="h-4 w-4" />
              <h3 className="text-xl font-semibold text-white">Automation guardrails</h3>
            </div>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-400">
              <li>Only evidence-backed resumes are tailored.</li>
              <li>Jobs below the profile threshold stay out of the ready queue.</li>
              <li>Final submission remains blocked until approval is complete.</li>
            </ul>
          </article>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-white">
              <CheckCircle2 className="h-4 w-4 text-emerald-300" />
              <h3 className="text-xl font-semibold">Scoring summary</h3>
            </div>
            <div className="mt-4 space-y-3">
              {[
                "Skill coverage checked against the active profile.",
                "Role fit and location fit remain profile-specific.",
                "Jobs with missing requirements are still surfaced, but clearly labeled.",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-slate-800 bg-white/5 p-4 text-sm leading-6 text-slate-300"
                >
                  {item}
                </div>
              ))}
            </div>
          </article>
        </aside>
      </div>
    </DashboardShell>
  );
}

