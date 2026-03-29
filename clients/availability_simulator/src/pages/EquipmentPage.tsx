import { useEffect, useState } from "react";
import {
  fetchSites,
  fetchAreas,
  fetchLines,
  fetchWorkCells,
  fetchEquipmentInWorkCell,
} from "../api/endpoints";
import DataTable, { type Column } from "../components/DataTable";
import type { Site, Area, ProductionLine, WorkCell, Equipment } from "../types";

interface Selection {
  siteId?: string;
  areaId?: string;
  lineId?: string;
  wcId?: string;
}

export default function EquipmentPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [lines, setLines] = useState<ProductionLine[]>([]);
  const [workCells, setWorkCells] = useState<WorkCell[]>([]);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [sel, setSel] = useState<Selection>({});
  const [loading, setLoading] = useState(false);

  // Load sites on mount
  useEffect(() => {
    fetchSites().then(setSites).catch(() => {});
  }, []);

  // Load areas when site changes
  useEffect(() => {
    setAreas([]); setLines([]); setWorkCells([]); setEquipment([]);
    if (!sel.siteId) return;
    fetchAreas(sel.siteId).then(setAreas).catch(() => {});
  }, [sel.siteId]);

  // Load lines when area changes
  useEffect(() => {
    setLines([]); setWorkCells([]); setEquipment([]);
    if (!sel.areaId) return;
    fetchLines(sel.areaId).then(setLines).catch(() => {});
  }, [sel.areaId]);

  // Load work cells when line changes
  useEffect(() => {
    setWorkCells([]); setEquipment([]);
    if (!sel.lineId) return;
    fetchWorkCells(sel.lineId).then(setWorkCells).catch(() => {});
  }, [sel.lineId]);

  // Load equipment when work cell changes
  useEffect(() => {
    setEquipment([]);
    if (!sel.wcId) return;
    setLoading(true);
    fetchEquipmentInWorkCell(sel.wcId)
      .then(setEquipment)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sel.wcId]);

  const equipColumns: Column<Equipment>[] = [
    { key: "code", header: "Code" },
    { key: "name", header: "Name" },
    { key: "equipment_type", header: "Type", render: (r) => r.equipment_type ?? "—" },
    { key: "status", header: "Status" },
    {
      key: "state_model_id",
      header: "State Model",
      render: (r) => r.state_model_id ?? <span className="text-gray-400">none</span>,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Hierarchy selectors */}
      <div className="flex flex-wrap gap-3">
        <Select
          label="Site"
          value={sel.siteId ?? ""}
          options={sites.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` }))}
          onChange={(v) => setSel({ siteId: v || undefined })}
        />
        <Select
          label="Area"
          value={sel.areaId ?? ""}
          options={areas.map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }))}
          onChange={(v) => setSel((p) => ({ ...p, areaId: v || undefined, lineId: undefined, wcId: undefined }))}
          disabled={!sel.siteId}
        />
        <Select
          label="Line"
          value={sel.lineId ?? ""}
          options={lines.map((l) => ({ value: l.id, label: `${l.code} — ${l.name}` }))}
          onChange={(v) => setSel((p) => ({ ...p, lineId: v || undefined, wcId: undefined }))}
          disabled={!sel.areaId}
        />
        <Select
          label="Work Cell"
          value={sel.wcId ?? ""}
          options={workCells.map((wc) => ({ value: wc.id, label: `${wc.code} — ${wc.name}` }))}
          onChange={(v) => setSel((p) => ({ ...p, wcId: v || undefined }))}
          disabled={!sel.lineId}
        />
      </div>

      {/* Equipment table */}
      {loading ? (
        <p className="text-gray-500 text-sm">Loading equipment…</p>
      ) : (
        <DataTable
          columns={equipColumns}
          data={equipment}
          emptyMessage={sel.wcId ? "No equipment in this work cell" : "Select a work cell above"}
        />
      )}

      {/* Quick summary */}
      {equipment.length > 0 && (
        <div className="flex gap-4 text-sm text-gray-600">
          <span>Total: <strong>{equipment.length}</strong></span>
          <span>
            With state model:{" "}
            <strong>{equipment.filter((e) => e.state_model_id).length}</strong>
          </span>
        </div>
      )}
    </div>
  );
}

/* ── Tiny select helper ─────────────────────────────────────────── */

function Select({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col text-xs font-medium text-gray-600">
      {label}
      <select
        className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm disabled:opacity-50"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        <option value="">— select —</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
