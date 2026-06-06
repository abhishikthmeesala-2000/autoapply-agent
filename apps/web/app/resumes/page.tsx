import { Download, FileCheck2, FileText, Stars } from "lucide-react";

import { DashboardShell } from "../../src/components/dashboard-shell";
import { getDashboardSnapshot, resolveActiveProfileId } from "../../src/lib/dashboard";

interface ResumesPageProps {
  searchParams?: {
    profile?: string;
  };
}

export default async function ResumesPage({ searchParams }: ResumesPageProps) {
  const snapshot = getDashboardSnapshot(resolveActiveProfileId(searchParams?.profile));

  return (
    <DashboardShell
      activeProfile={snapshot.profile}
      activeSection="resumes"
      profiles={snapshot.profiles}
      currentPath="/resumes"
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
        <section className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-semibold text-white">Tailored versions</h3>
                <p className="mt-1 text-sm text-slate-400">
                  Every export is ATS-safe and traceable to source evidence.
                </p>
              </div>
              <Download className="h-5 w-5 text-slate-400" />
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {snapshot.resumeVersions.map((resumeVersion) => (
                <article
                  key={resumeVersion.id}
                  className="rounded-2xl border border-slate-800 bg-white/5 p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="text-lg font-semibold text-white">
                        {resumeVersion.title}
                      </h4>
                      <p className="mt-1 text-sm text-slate-400">
                        {resumeVersion.jobTitle}
                      </p>
                    </div>
                    <span className="rounded-full bg-emerald-400/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
                      ATS {resumeVersion.atsScore}
                    </span>
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-sm text-slate-300">
                    <FileCheck2 className="h-4 w-4 text-slate-500" />
                    Export {resumeVersion.exportReady ? "ready" : "blocked"}
                  </div>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                    Updated {resumeVersion.updatedAt}
                  </p>
                </article>
              ))}
            </div>
          </article>
        </section>

        <aside className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-cyan-300">
              <FileText className="h-4 w-4" />
              <h3 className="text-xl font-semibold text-white">Document export</h3>
            </div>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              Phase 11 exports DOCX first and then bundles the PDF alongside it. The
              dashboard surfaces those exports here so the user can audit what was
              generated before anything leaves the system.
            </p>
          </article>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-white">
              <Stars className="h-4 w-4 text-cyan-300" />
              <h3 className="text-xl font-semibold">ATS notes</h3>
            </div>
            <div className="mt-4 space-y-3 text-sm leading-6 text-slate-400">
              <p>Readable section headings stay in uppercase for extraction.</p>
              <p>Bullets remain short and text-based to avoid layout issues.</p>
              <p>All export data remains linked to the active profile only.</p>
            </div>
          </article>
        </aside>
      </div>
    </DashboardShell>
  );
}

