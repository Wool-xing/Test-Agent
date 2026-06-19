import React, { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

type NavSection = "dashboard" | "tests" | "agents" | "marketplace" | "settings";

interface EngineStatus {
  version: string;
  connected: boolean;
}

const NAV_ITEMS: { id: NavSection; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "tests", label: "Tests" },
  { id: "agents", label: "Agents" },
  { id: "marketplace", label: "Marketplace" },
  { id: "settings", label: "Settings" },
];

const PlaceholderPanel: React.FC<{ section: NavSection }> = ({ section }) => {
  const descriptions: Record<NavSection, string> = {
    dashboard: "Overview of test runs, pass rates, release readiness scores, and system health.",
    tests: "Browse and execute test suites. View flaky test reports and impact analysis results.",
    agents: "Manage the 16 AI testing agents. Assign roles, view expert heatmaps, and configure agent behavior.",
    marketplace: "Discover and install plugins via entry_points. Browse agents, skills, and backends from the community.",
    settings: "Configure API keys, RBAC roles, audit logging, multi-tenancy, and execution hooks.",
  };

  return (
    <div style={{ padding: "32px" }}>
      <h2 style={{ margin: "0 0 12px 0", fontSize: "20px", fontWeight: 600 }}>
        {section.charAt(0).toUpperCase() + section.slice(1)}
      </h2>
      <p style={{ color: "#666", margin: 0 }}>{descriptions[section]}</p>
    </div>
  );
};

const App: React.FC = () => {
  const [activeSection, setActiveSection] = useState<NavSection>("dashboard");
  const [engineStatus, setEngineStatus] = useState<EngineStatus>({
    version: "...",
    connected: false,
  });

  useEffect(() => {
    invoke<string>("get_version")
      .then((version) => setEngineStatus({ version, connected: true }))
      .catch(() => setEngineStatus({ version: "N/A", connected: false }));
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
      {/* Sidebar */}
      <nav
        style={{
          width: 220,
          minWidth: 220,
          background: "#1a1a2e",
          color: "#e0e0e0",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            padding: "20px 16px",
            fontSize: "16px",
            fontWeight: 700,
            letterSpacing: "0.5px",
            borderBottom: "1px solid #2a2a4a",
          }}
        >
          Test-Agent V2
        </div>

        <ul style={{ listStyle: "none", margin: 0, padding: "8px 0", flex: 1 }}>
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => setActiveSection(item.id)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "10px 20px",
                  border: "none",
                  background: activeSection === item.id ? "#16213e" : "transparent",
                  color: activeSection === item.id ? "#7ec8e3" : "#a0a0b0",
                  cursor: "pointer",
                  fontSize: "14px",
                  transition: "background 0.15s",
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Main area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#f5f5f5" }}>
        {/* Content */}
        <main style={{ flex: 1, overflow: "auto" }}>
          <PlaceholderPanel section={activeSection} />
        </main>

        {/* Status bar */}
        <footer
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "6px 16px",
            background: "#e8e8e8",
            borderTop: "1px solid #d0d0d0",
            fontSize: "12px",
            color: "#555",
          }}
        >
          <span>
            Engine:{" "}
            <span
              style={{
                color: engineStatus.connected ? "#2d8a4e" : "#c0392b",
                fontWeight: 600,
              }}
            >
              {engineStatus.connected ? "Connected" : "Offline"}
            </span>
          </span>
          <span>Version {engineStatus.version}</span>
        </footer>
      </div>
    </div>
  );
};

export default App;
