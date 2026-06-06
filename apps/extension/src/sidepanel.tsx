import type { FC } from "react";

import {
  autofillSafetyNotes,
  getPanelStatusMessage,
  panelHighlights,
} from "./lib/panel";

const SidePanel: FC = () => {
  return (
    <div
      style={{
        minWidth: 320,
        minHeight: 560,
        padding: 20,
        fontFamily:
          'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        background: "linear-gradient(180deg, #0f172a 0%, #020617 100%)",
        color: "#e2e8f0",
      }}
    >
      <div
        style={{
          border: "1px solid rgba(148, 163, 184, 0.2)",
          borderRadius: 20,
          padding: 16,
          background: "rgba(15, 23, 42, 0.72)",
          boxShadow: "0 24px 80px rgba(15, 23, 42, 0.35)",
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: 12,
            letterSpacing: "0.24em",
            color: "#94a3b8",
          }}
        >
          CAREEROS AI
        </p>
        <h1 style={{ margin: "10px 0 8px", fontSize: 24, lineHeight: 1.2 }}>
          Autofill Engine
        </h1>
        <p style={{ margin: 0, color: "#cbd5e1", lineHeight: 1.6 }}>
          {getPanelStatusMessage("the current application page")}
        </p>

        <div style={{ marginTop: 18 }}>
          <p style={{ margin: "0 0 8px", fontSize: 13, color: "#94a3b8" }}>
            Phase 13 capabilities
          </p>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              color: "#e2e8f0",
              lineHeight: 1.8,
            }}
          >
            {panelHighlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div
          style={{
            marginTop: 18,
            borderRadius: 16,
            padding: 14,
            background: "rgba(14, 165, 233, 0.12)",
            border: "1px solid rgba(14, 165, 233, 0.2)",
            color: "#bae6fd",
          }}
        >
          The extension prepares forms, flags uncertain answers, and stops
          before final submission.
        </div>

        <div
          style={{
            marginTop: 14,
            borderRadius: 16,
            padding: 14,
            background: "rgba(250, 204, 21, 0.08)",
            border: "1px solid rgba(250, 204, 21, 0.18)",
            color: "#fef3c7",
          }}
        >
          <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Safety notes</p>
          <ul style={{ margin: "10px 0 0", paddingLeft: 18, lineHeight: 1.7 }}>
            {autofillSafetyNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default SidePanel;

