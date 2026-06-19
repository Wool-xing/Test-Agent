import React from "react";
import type { Plugin } from "../App";

interface Props {
  plugin: Plugin;
  onConfirm: () => void;
  onCancel: () => void;
}

export function InstallModal({ plugin, onConfirm, onCancel }: Props) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Install {plugin.name}?</h2>
        <p>
          This will install <strong>{plugin.name}</strong> v{plugin.version}
          {plugin.author ? ` by ${plugin.author}` : ""}.
        </p>
        <p>
          {plugin.license ? `License: ${plugin.license}. ` : ""}
          {plugin.safety_score !== undefined ? `Safety score: ${plugin.safety_score}/100. ` : ""}
          Please review the source before installing.
        </p>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={onConfirm}>
            Confirm Install
          </button>
        </div>
      </div>
    </div>
  );
}
