import {
  ArrowUpRight,
  Briefcase,
  CheckCircle2,
  Clock3,
  LayoutDashboard,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

import { metricCards, pipelineStages } from "../src/lib/dashboard";

const recentActions = [
  {
    title: "Tailored resume prepared",
    detail: "Senior Product Engineer at Ashby",
    time: "2m ago",
  },
  {
    title: "Job scored",
    detail: "Frontend Engineer at Greenhouse source",
    time: "11m ago",
  },
  {
    title: "Approval required",
    detail: "Sensitive answer flagged for manual review",
    time: "27m ago",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-glow backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-cyan-400/15 text-cyan-300">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">CareerOS AI</p>
              <h1 className="text-lg font-semibold text-white">
                Command Center
              </h1>
            </div>
          </div>

          <nav className="mt-8 space-y-2 text-sm">
            {[
              "Command Center",
              "Profiles",
              "Master Resume",
              "Jobs",
              "Approval Center",
              "Agent Runs",
            ].map((item, index) => (
              <a
                key={item}
                className={`flex items-center gap-3 rounded-2xl px-3 py-3 transition ${
                  index === 0
                    ? "bg-white/8 text-white"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
                href="#"
              >
                {index === 0 ? (
                  <LayoutDashboard className="h-4 w-4" />
                ) : (
                  <Briefcase className="h-4 w-4" />
                )}
                {item}
              </a>
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
            <div className="flex items-center gap-2 text-emerald-300">
              <ShieldCheck className="h-4 w-4" />
              <p className="text-sm font-medium">Safe by design</p>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Applications pause before submission until a human approves the
              final step.
            </p>
          </div>
        </aside>

        <section className="space-y-6">
          <header className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6 shadow-glow backdrop-blur">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.25em] text-slate-400">
                  Local-first AI career operating system
                </p>
                <h2 className="mt-2 text-3xl font-semibold text-white">
                  Jobs, resumes, and approvals in one control plane.
                </h2>
              </div>
              <div className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-300">
                Active profile:{" "}
                <span className="font-semibold text-white">
                  Product Engineer
                </span>
              </div>
            </div>
          </header>

          <div className="grid gap-4 md:grid-cols-3">
            {metricCards.map((metric) => (
              <article
                key={metric.label}
                className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-glow"
              >
                <p className="text-sm text-slate-400">{metric.label}</p>
                <div className="mt-4 flex items-end justify-between">
                  <p className="text-4xl font-semibold text-white">
                    {metric.value}
                  </p>
                  <span className="inline-flex items-center gap-1 rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-300">
                    {metric.delta}
                    <ArrowUpRight className="h-3 w-3" />
                  </span>
                </div>
              </article>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
            <article className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6 shadow-glow">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-semibold text-white">
                    Application pipeline
                  </h3>
                  <p className="mt-1 text-sm text-slate-400">
                    Human-in-the-loop workflow with safe autofill and approval
                    gating.
                  </p>
                </div>
                <Clock3 className="h-5 w-5 text-slate-400" />
              </div>

              <div className="mt-6 grid gap-3 md:grid-cols-4">
                {pipelineStages.map((stage) => (
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

            <article className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6 shadow-glow">
              <h3 className="text-xl font-semibold text-white">
                Live activity
              </h3>
              <div className="mt-5 space-y-4">
                {recentActions.map((action) => (
                  <div
                    key={action.title}
                    className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-white">{action.title}</p>
                      <span className="text-xs text-slate-500">
                        {action.time}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-400">
                      {action.detail}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                Final submission is disabled until explicit user approval.
              </div>
              <div className="mt-4 inline-flex items-center gap-2 text-sm text-cyan-300">
                <CheckCircle2 className="h-4 w-4" />
                Ready for Phase 2 database wiring
              </div>
            </article>
          </div>
        </section>
      </div>
    </main>
  );
}
