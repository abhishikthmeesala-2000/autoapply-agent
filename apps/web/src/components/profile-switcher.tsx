import Link from "next/link";
import { Check } from "lucide-react";

import {
  getNavigationHref,
  type ProfileSummary,
} from "../lib/dashboard";

interface ProfileSwitcherProps {
  profiles: ProfileSummary[];
  activeProfileId: string;
  basePath: string;
}

export function ProfileSwitcher({
  profiles,
  activeProfileId,
  basePath,
}: ProfileSwitcherProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {profiles.map((profile) => {
        const active = profile.id === activeProfileId;

        return (
          <Link
            key={profile.id}
            href={getNavigationHref(basePath, profile.id)}
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition ${
              active
                ? "border-cyan-400/40 bg-cyan-400/15 text-cyan-100"
                : "border-slate-700 bg-slate-950/60 text-slate-300 hover:border-slate-500 hover:text-white"
            }`}
          >
            {active ? <Check className="h-3.5 w-3.5" /> : null}
            <span className="font-medium">{profile.name}</span>
            <span className="text-[11px] uppercase tracking-[0.22em] text-slate-400">
              {profile.location}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
