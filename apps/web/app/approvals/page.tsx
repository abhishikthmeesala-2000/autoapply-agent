import { AlertTriangle, CircleCheckBig, MousePointerClick, ShieldAlert } from "lucide-react";

import { DashboardShell } from "../../src/components/dashboard-shell";
import { getDashboardSnapshot, resolveActiveProfileId } from "../../src/lib/dashboard";

interface ApprovalsPageProps {
  searchParams?: {
    profile?: string;
  };
}

export default async function ApprovalsPage({ searchParams }: ApprovalsPageProps) {
  const snapshot = getDashboardSnapshot(resolveActiveProfileId(searchParams?.profile));

  return (
    <DashboardShell
      activeProfile={snapshot.profile}
      activeSection="approvals"
      profiles={snapshot.profiles}
      currentPath="/approvals"
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <section className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-amber-200">
              <ShieldAlert className="h-4 w-4" />
              <h3 className="text-xl font-semibold text-white">Review queue</h3>
            </div>
            <div className="mt-5 space-y-4">
              {snapshot.approvals.map((approval) => (
                <div
                  key={approval.id}
                  className="rounded-2xl border border-amber-500/20 bg-amber-500/8 p-4"
                >
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-medium text-white">{approval.title}</p>
                    <AlertTriangle className="h-4 w-4 text-amber-300" />
                  </div>
                  <p className="mt-2 text-sm text-slate-300">{approval.detail}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    {approval.reason}
                  </p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <aside className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-emerald-300">
              <CircleCheckBig className="h-4 w-4" />
              <h3 className="text-xl font-semibold text-white">Trusted answers</h3>
            </div>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              The autofill engine should only reuse profile data that has been
              explicitly marked as safe. Anything ambiguous stays here until it is
              reviewed by a human.
            </p>
          </article>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-white">
              <MousePointerClick className="h-4 w-4 text-cyan-300" />
              <h3 className="text-xl font-semibold">Submission flow</h3>
            </div>
            <div className="mt-4 space-y-3 text-sm leading-6 text-slate-400">
              <p>Detect the field.</p>
              <p>Fill trusted data.</p>
              <p>Flag uncertainty for review.</p>
              <p>Stop before the submit button.</p>
            </div>
          </article>
        </aside>
      </div>
    </DashboardShell>
  );
}

