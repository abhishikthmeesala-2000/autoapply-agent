"use client";

import { PauseCircle, PlayCircle, Power } from "lucide-react";
import { useState, useTransition } from "react";

import { getApiBaseUrl } from "../lib/api";

interface AgentControlsProps {
  profileId: string;
}

interface AgentControlPayload {
  summary?: string;
  status?: string;
  metadata?: {
    jobs_discovered?: number;
    jobs_scored?: number;
    applications_prepared?: number;
    daily_limit_reached?: boolean;
    notes?: string[];
    error?: string | null;
  };
}

export function AgentControls({ profileId }: AgentControlsProps) {
  const [statusText, setStatusText] = useState("Ready");
  const [details, setDetails] = useState<string[]>([]);
  const [isPending, startTransition] = useTransition();

  const sendAction = (action: "start" | "pause" | "stop") => {
    startTransition(async () => {
      setStatusText(`Sending ${action} request...`);
      setDetails([]);

      try {
        const response = await fetch(
          `${getApiBaseUrl()}/profiles/${profileId}/agent/${action}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          },
        );

        const payload = (await response.json()) as AgentControlPayload;
        if (!response.ok) {
          throw new Error(payload.summary || `HTTP ${response.status}`);
        }

        setStatusText(payload.summary || `${action} complete.`);
        setDetails(
          [
            `Run status: ${payload.status ?? "unknown"}`,
            `Jobs discovered: ${payload.metadata?.jobs_discovered ?? 0}`,
            `Jobs scored: ${payload.metadata?.jobs_scored ?? 0}`,
            `Applications prepared: ${payload.metadata?.applications_prepared ?? 0}`,
            payload.metadata?.daily_limit_reached ? "Daily limit reached." : null,
            ...(payload.metadata?.notes ?? []),
          ].filter(Boolean) as string[],
        );
      } catch (error) {
        setStatusText(error instanceof Error ? error.message : "Agent action failed.");
      }
    });
  };

  const controls = [
    {
      action: "start" as const,
      icon: PlayCircle,
      label: "Start",
      tone: "emerald",
    },
    {
      action: "pause" as const,
      icon: PauseCircle,
      label: "Pause",
      tone: "amber",
    },
    {
      action: "stop" as const,
      icon: Power,
      label: "Stop",
      tone: "slate",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {controls.map((control) => {
          const Icon = control.icon;
          return (
            <button
              key={control.label}
              type="button"
              disabled={isPending}
              onClick={() => sendAction(control.action)}
              className="flex items-center justify-between rounded-2xl border border-slate-800 bg-white/5 px-4 py-3 text-left text-sm text-white transition hover:border-cyan-400/30 hover:bg-cyan-400/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span>{control.label} agent mode</span>
              <Icon className="h-4 w-4 text-cyan-300" />
            </button>
          );
        })}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
          Status
        </p>
        <p className="mt-2 text-sm leading-6 text-white">{statusText}</p>
        <div className="mt-3 space-y-2 text-sm text-slate-400">
          {details.length > 0 ? (
            details.map((detail) => <p key={detail}>{detail}</p>)
          ) : (
            <p>Final submission stays blocked until approval is explicit.</p>
          )}
        </div>
      </div>
    </div>
  );
}

