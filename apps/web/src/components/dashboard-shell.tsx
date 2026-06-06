import Link from "next/link";
import {
  BrainCircuit,
  BriefcaseBusiness,
  ShieldCheck,
  Sparkles,
  Waves,
} from "lucide-react";
import type { ReactNode } from "react";

import { loadApiConnectionState } from "../lib/api";
import {
  getNavigationHref,
  navigationItems,
  type DashboardSectionKey,
  type ProfileSummary,
} from "../lib/dashboard";
import { ProfileSwitcher } from "./profile-switcher";

interface DashboardShellProps {
  activeProfile: ProfileSummary;
  activeSection: DashboardSectionKey;
  profiles: ProfileSummary[];
  currentPath: string;
  children: ReactNode;
}

export async function DashboardShell({
  activeProfile,
  activeSection,
  profiles,
  currentPath,
  children,
}: DashboardShellProps) {
  const connection = await loadApiConnectionState();

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-[1540px] gap-6 xl:grid-cols-[290px_1fr]">
        <aside className="rounded-[2rem] border border-slate-800/80 bg-slate-950/75 p-5 shadow-glow backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-cyan-400/15 text-cyan-300">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">CareerOS AI</p>
              <h1 className="text-lg font-semibold text-white">Dashboard</h1>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-cyan-400/15 bg-cyan-400/5 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-cyan-200/80">
              Active profile
            </p>
            <p className="mt-2 text-lg font-semibold text-white">
              {activeProfile.name}
            </p>
            <p className="mt-1 text-sm leading-6 text-slate-300">
              {activeProfile.headline}
            </p>
          </div>

          <nav className="mt-6 space-y-2 text-sm">
            {navigationItems.map((item) => {
              const active = item.section === activeSection;

              return (
                <Link
                  key={item.label}
                  className={`flex items-start gap-3 rounded-2xl px-3 py-3 transition ${
                    active
                      ? "bg-white/8 text-white"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  }`}
                  href={getNavigationHref(item.href, activeProfile.id)}
                >
                  <span className="mt-0.5">
                    {item.section === "overview" ? (
                      <Waves className="h-4 w-4" />
                    ) : (
                      <BriefcaseBusiness className="h-4 w-4" />
                    )}
                  </span>
                  <span>
                    <span className="block font-medium">{item.label}</span>
                    <span className="mt-0.5 block text-xs leading-5 text-slate-500">
                      {item.description}
                    </span>
                  </span>
                </Link>
              );
            })}
          </nav>

          <div className="mt-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
            <div className="flex items-center gap-2 text-emerald-300">
              <ShieldCheck className="h-4 w-4" />
              <p className="text-sm font-medium">Approval-first workflow</p>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Final submission stays locked until a human confirms any sensitive
              response or risky autofill field.
            </p>
          </div>
        </aside>

        <section className="space-y-6">
          <header className="rounded-[2rem] border border-slate-800/80 bg-slate-950/75 p-6 shadow-glow backdrop-blur">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
                  Local-first AI career operating system
                </p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  Applications, resumes, and approvals in one control plane.
                </h2>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-400">
                  Use the profile switcher to pivot between candidates, inspect
                  live job pipeline state, and wire the dashboard to the local
                  API when it is available.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                    API bridge
                  </p>
                  <div className="mt-2 flex items-center gap-2 text-sm">
                    <span
                      className={`inline-flex h-2.5 w-2.5 rounded-full ${
                        connection.reachable ? "bg-emerald-400" : "bg-amber-400"
                      }`}
                    />
                    <span className="font-medium text-white">
                      {connection.reachable ? "Connected" : "Mock fallback"}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    {connection.baseUrl} • {connection.statusText}
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                    Active profile
                  </p>
                  <div className="mt-2 flex items-center gap-2 text-sm text-white">
                    <BrainCircuit className="h-4 w-4 text-cyan-300" />
                    <span className="font-medium">{activeProfile.focus}</span>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    {activeProfile.location} • {activeProfile.status}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                Profile switcher
              </p>
              <div className="mt-3">
                <ProfileSwitcher
                  activeProfileId={activeProfile.id}
                  profiles={profiles}
                  basePath={currentPath}
                />
              </div>
            </div>
          </header>

          {children}
        </section>
      </div>
    </main>
  );
}
