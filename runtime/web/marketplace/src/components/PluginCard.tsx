import React from "react";
import type { Plugin } from "../App";

interface Props {
  plugin: Plugin;
  onInstall: (plugin: Plugin) => void;
}

function StarRating({ rating }: { rating: number }) {
  const full = Math.round(rating);
  const stars = Array.from({ length: 5 }, (_, i) => (i < full ? "★" : "☆"));
  return (
    <span className="star-rating">
      {stars.join("")} {rating > 0 ? rating.toFixed(1) : ""}
    </span>
  );
}

export function PluginCard({ plugin, onInstall }: Props) {
  return (
    <div className="plugin-card">
      <div className="plugin-card-header">
        <h3>{plugin.name}</h3>
        <span className={`plugin-type-badge ${plugin.plugin_type}`}>{plugin.plugin_type}</span>
      </div>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 8 }}>
        v{plugin.version}
        {plugin.author ? ` · ${plugin.author}` : ""}
      </p>
      <div className="plugin-card-meta">
        <StarRating rating={plugin.rating} />
        <span>{plugin.downloads.toLocaleString()} installs</span>
      </div>
      {plugin.tags.length > 0 && (
        <div className="plugin-card-tags">
          {plugin.tags.map((t) => (
            <span key={t} className="tag">
              {t}
            </span>
          ))}
        </div>
      )}
      <div className="plugin-card-actions">
        <button className="btn btn-primary" onClick={() => onInstall(plugin)} disabled={plugin.installed}>
          {plugin.installed ? "Installed" : "Install"}
        </button>
        {plugin.source_url && (
          <a
            href={plugin.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}
          >
            Source
          </a>
        )}
      </div>
    </div>
  );
}
