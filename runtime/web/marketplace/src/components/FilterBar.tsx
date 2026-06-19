import React from "react";

interface Props {
  type: string;
  onTypeChange: (type: string) => void;
  sort: string;
  onSortChange: (sort: string) => void;
}

const PLUGIN_TYPES = [
  { value: "", label: "All Types" },
  { value: "agent", label: "Agent" },
  { value: "skill", label: "Skill" },
  { value: "tool", label: "Tool" },
  { value: "gate", label: "Gate" },
];

const SORT_OPTIONS = [
  { value: "stars", label: "Top Rated" },
  { value: "downloads", label: "Most Installed" },
  { value: "newest", label: "Newest" },
  { value: "name", label: "Name A-Z" },
];

export function FilterBar({ type, onTypeChange, sort, onSortChange }: Props) {
  return (
    <>
      <select className="filter-select" value={type} onChange={(e) => onTypeChange(e.target.value)}>
        {PLUGIN_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      <select className="filter-select" value={sort} onChange={(e) => onSortChange(e.target.value)}>
        {SORT_OPTIONS.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </>
  );
}
