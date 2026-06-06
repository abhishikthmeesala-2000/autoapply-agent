import { BadgeCheck, MapPin, Shuffle, Users } from "lucide-react";

import { DashboardShell } from "../../src/components/dashboard-shell";
import { getDashboardSnapshot, resolveActiveProfileId } from "../../src/lib/dashboard";

interface ProfilesPageProps {
  searchParams?: {
    profile?: string;
  };
}

export default async function ProfilesPage({ searchParams }: ProfilesPageProps) {
  const snapshot = getDashboardSnapshot(resolveActiveProfileId(searchParams?.profile));

  return (
    <DashboardShell
      activeProfile={snapshot.profile}
      activeSection="profiles"
      profiles={snapshot.profiles}
      currentPath="/profiles"
    >
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            {snapshot.profiles.map((profile) => (
              <article
                key={profile.id}
                className={`rounded-[1.75rem] border p-5 shadow-glow ${
                  profile.id === snapshot.activeProfileId
                    ? "border-cyan-400/30 bg-cyan-400/10"
                    : "border-slate-800/80 bg-slate-950/75"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-lg font-semibold text-white">{profile.name}</h3>
                  <BadgeCheck className="h-4 w-4 text-emerald-300" />
                </div>
                <p className="mt-2 text-sm text-slate-400">{profile.headline}</p>
                <div className="mt-4 space-y-2 text-sm text-slate-300">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-slate-500" />
                    {profile.location}
                  </div>
                  <p>{profile.focus}</p>
                </div>
              </article>
            ))}
          </div>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-cyan-300">
              <Shuffle className="h-4 w-4" />
              <h3 className="text-xl font-semibold text-white">
                Profile switcher behavior
              </h3>
            </div>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-400">
              The switcher uses query parameters, so the current dashboard page
              stays intact while the active profile changes. That keeps the
              dashboard stateless, predictable, and easy to share.
            </p>
          </article>
        </section>

        <aside className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <div className="flex items-center gap-2 text-white">
              <Users className="h-4 w-4 text-cyan-300" />
              <h3 className="text-xl font-semibold">Current profile</h3>
            </div>
            <div className="mt-4 rounded-2xl border border-slate-800 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                Selected candidate
              </p>
              <p className="mt-2 text-2xl font-semibold text-white">
                {snapshot.profile.name}
              </p>
              <p className="mt-2 text-sm text-slate-400">
                {snapshot.profile.headline}
              </p>
            </div>
          </article>

          <article className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow">
            <h3 className="text-xl font-semibold text-white">Profile notes</h3>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-400">
              <li>Each profile keeps its own job sources, approvals, and exports.</li>
              <li>Profile-scoped routes must always include the profile identifier.</li>
              <li>The dashboard remains local-first even when the API is offline.</li>
            </ul>
          </article>
        </aside>
      </div>
    </DashboardShell>
  );
}

