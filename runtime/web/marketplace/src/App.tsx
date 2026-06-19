import React, { useState, useEffect, useCallback } from "react";
import { SearchBar } from "./components/SearchBar";
import { FilterBar } from "./components/FilterBar";
import { PluginCard } from "./components/PluginCard";
import { InstallModal } from "./components/InstallModal";

export interface Plugin {
  name: string;
  version: string;
  description: string;
  author: string;
  plugin_type: "agent" | "skill" | "tool" | "gate" | "profile";
  downloads: number;
  rating: number;
  tags: string[];
  source_url?: string;
  license?: string;
  safety_score?: number;
  installed?: boolean;
}

const API_BASE = "/api/marketplace";

export function MarketplaceApp() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [filterType, setFilterType] = useState("");
  const [sortBy, setSortBy] = useState("stars");
  const [installTarget, setInstallTarget] = useState<Plugin | null>(null);

  const fetchPlugins = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      if (filterType) params.set("type", filterType);
      params.set("sort", sortBy);
      params.set("limit", "50");

      const res = await fetch(`${API_BASE}/plugins?${params}`);
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      setPlugins(data.plugins || []);
    } catch (err) {
      console.error("Failed to fetch plugins:", err);
      setPlugins([]);
    } finally {
      setLoading(false);
    }
  }, [query, filterType, sortBy]);

  useEffect(() => {
    fetchPlugins();
  }, [fetchPlugins]);

  const handleInstall = (plugin: Plugin) => {
    setInstallTarget(plugin);
  };

  const confirmInstall = () => {
    // In a full implementation, this would call POST /api/marketplace/install
    alert(`Installing ${installTarget?.name}...\n\nRun: tagent install ${installTarget?.name}`);
    setInstallTarget(null);
  };

  return (
    <div className="container">
      <header className="header">
        <h1>Test-Agent Marketplace</h1>
        <p>Browse and install plugins for Test-Agent V2.0.0</p>
      </header>

      <div className="search-filter-row">
        <SearchBar value={query} onChange={setQuery} />
        <FilterBar type={filterType} onTypeChange={setFilterType} sort={sortBy} onSortChange={setSortBy} />
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
        </div>
      ) : plugins.length === 0 ? (
        <div className="empty-state">
          <p>No plugins found.</p>
          {query && <p>Try a different search term.</p>}
        </div>
      ) : (
        <div className="plugin-grid">
          {plugins.map((p) => (
            <PluginCard key={p.name} plugin={p} onInstall={handleInstall} />
          ))}
        </div>
      )}

      {installTarget && (
        <InstallModal plugin={installTarget} onConfirm={confirmInstall} onCancel={() => setInstallTarget(null)} />
      )}
    </div>
  );
}
