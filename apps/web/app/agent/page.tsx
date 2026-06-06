import { PauseCircle, PlayCircle, Power, Workflow } from "lucide-react";

import { DashboardShell } from "../../src/components/dashboard-shell";
import { getDashboardSnapshot, resolveActiveProfileId } from "../../src/lib/dashboard";

interface AgentPageProps {
  searchParams?: {
    profile?: string;
  };
}

export default async function AgentPage({ searchParams }: AgentPageProps) {
  const snapshot = getDashboardSnapshot(resolveActiveProfileId(searchParams?.profile));

  return (
    <DashboardShell
      activeProfile={snapshot.profile}
      activeSection="agent"
      profiles={snapshot.profiles}
      currentPath="/agent"
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_0.92fr]">
        <section className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-cyan-300">
              <Workflow className="h-4 w-4" />
              <h3 className="text-xl font-semibold text-white">Agent runs</h3>
            </div>
            <div className="mt-5 space-y-4">
              {snapshot.agentRuns.map((run) => (
                <div
                  key={run.id}
                  className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                >
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-medium text-white">{run.label}</p>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                        run.status === "running"
                          ? "bg-emerald-400/10 text-emerald-300"
                          : run.status === "paused"
                            ? "bg-amber-400/10 text-amber-200"
                            : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {run.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {run.nextStep}
                  </p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <aside className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <h3 className="text-xl font-semibold text-white">Controls</h3>
            <div className="mt-5 grid gap-3">
              {[
                { icon: PlayCircle, label: "Start" },
                { icon: PauseCircle, label: "Pause" },
                { icon: Power, label: "Stop" },
              ].map((control) => {
                const Icon = control.icon;

                return (
                  <button
                    key={control.label}
                    type="button"
                    className="flex items-center justify-between rounded-2xl border border-slate-800 bg-white/5 px-4 py-3 text-left text-sm text-white transition hover:border-cyan-400/30 hover:bg-cyan-400/10"
                  >
                    <span>{control.label} agent mode</span>
                    <Icon className="h-4 w-4 text-cyan-300" />
                  </button>
                );
              })}
            </div>
          </article>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
              Continuous mode
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              The continuous agent should respect limits, wait for approval
              before submission, and keep the user in control of the timeline.
            </p>
          </article>
        </aside>
      </div>
    </DashboardShell>
  );
}

