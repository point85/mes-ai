import { useState, useEffect } from "react";
import {
  fetchSites,
  fetchAreas,
  fetchProductionLines,
  fetchWorkCells,
  fetchEquipmentInWorkCell,
} from "../api/runtime";
import type { Site, Area, ProductionLine, WorkCell, Equipment } from "../types";

// ── Node kinds used by the checkbox callback ──────────────────────

export type TreeNodeKind = "site" | "area" | "line" | "workcell" | "equipment";

export interface CheckedNode {
  id: string;
  kind: TreeNodeKind;
  code: string;
  name: string;
}

interface EquipmentTreeProps {
  selectedEquipmentId: string | null;
  onSelectEquipment: (equip: Equipment) => void;
  /** Currently checked node IDs (controlled from parent). */
  checkedNodeIds: Set<string>;
  /** Called when a checkbox is toggled with the node details. */
  onToggleCheck: (node: CheckedNode) => void;
}

type ChildNode = Area | ProductionLine | WorkCell | Equipment;

export default function EquipmentTree({
  selectedEquipmentId,
  onSelectEquipment,
  checkedNodeIds,
  onToggleCheck,
}: EquipmentTreeProps) {
  const [sites, setSites] = useState<Site[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [childMap, setChildMap] = useState<Record<string, ChildNode[]>>({});
  const [loading, setLoading] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchSites().then(setSites).catch(() => {});
  }, []);

  async function toggleExpand(
    id: string,
    fetcher: (parentId: string) => Promise<ChildNode[]>,
  ) {
    const wasExpanded = expanded.has(id);
    setExpanded((prev) => {
      const next = new Set(prev);
      if (wasExpanded) next.delete(id);
      else next.add(id);
      return next;
    });
    if (!wasExpanded && !childMap[id]) {
      setLoading((p) => new Set(p).add(id));
      try {
        const data = await fetcher(id);
        setChildMap((p) => ({ ...p, [id]: data }));
      } catch {
        /* ignore */
      }
      setLoading((p) => {
        const n = new Set(p);
        n.delete(id);
        return n;
      });
    }
  }

  const Chevron = ({ open }: { open: boolean }) => (
    <svg
      className={`w-3 h-3 shrink-0 text-gray-400 transition-transform ${open ? "rotate-90" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );

  const Spinner = () => (
    <span className="text-[10px] text-gray-400 animate-pulse ml-auto">…</span>
  );

  function Checkbox({ node }: { node: CheckedNode }) {
    return (
      <input
        type="checkbox"
        checked={checkedNodeIds.has(node.id)}
        onChange={(e) => {
          e.stopPropagation();
          onToggleCheck(node);
        }}
        onClick={(e) => e.stopPropagation()}
        className="h-3.5 w-3.5 rounded border-gray-400 text-indigo-600 focus:ring-indigo-500 shrink-0 cursor-pointer"
      />
    );
  }

  const branchCls =
    "flex items-center gap-1.5 py-1 cursor-pointer rounded hover:bg-gray-100";

  return (
    <div className="text-sm select-none">
      {sites.length === 0 && (
        <p className="px-2 py-3 text-xs text-gray-400">Loading sites…</p>
      )}
      {sites.map((site) => (
        <div key={site.id}>
          <div
            className={branchCls}
            style={{ paddingLeft: 4 }}
            onClick={() => toggleExpand(site.id, fetchAreas)}
          >
            <Chevron open={expanded.has(site.id)} />
            <Checkbox node={{ id: site.id, kind: "site", code: site.code, name: site.name }} />
            <span className="text-[10px] font-mono text-gray-400 shrink-0">S</span>
            <span className="truncate" title={site.name}>{site.code}</span>
            {loading.has(site.id) && <Spinner />}
          </div>

          {expanded.has(site.id) &&
            ((childMap[site.id] as Area[] | undefined) ?? []).map((area) => (
              <div key={area.id}>
                <div
                  className={branchCls}
                  style={{ paddingLeft: 20 }}
                  onClick={() => toggleExpand(area.id, fetchProductionLines)}
                >
                  <Chevron open={expanded.has(area.id)} />
                  <Checkbox node={{ id: area.id, kind: "area", code: area.code, name: area.name }} />
                  <span className="text-[10px] font-mono text-gray-400 shrink-0">A</span>
                  <span className="truncate" title={area.name}>{area.code}</span>
                  {loading.has(area.id) && <Spinner />}
                </div>

                {expanded.has(area.id) &&
                  ((childMap[area.id] as ProductionLine[] | undefined) ?? []).map((line) => (
                    <div key={line.id}>
                      <div
                        className={branchCls}
                        style={{ paddingLeft: 36 }}
                        onClick={() => toggleExpand(line.id, fetchWorkCells)}
                      >
                        <Chevron open={expanded.has(line.id)} />
                        <Checkbox node={{ id: line.id, kind: "line", code: line.code, name: line.name }} />
                        <span className="text-[10px] font-mono text-gray-400 shrink-0">L</span>
                        <span className="truncate" title={line.name}>{line.code}</span>
                        {loading.has(line.id) && <Spinner />}
                      </div>

                      {expanded.has(line.id) &&
                        ((childMap[line.id] as WorkCell[] | undefined) ?? []).map((wc) => (
                          <div key={wc.id}>
                            <div
                              className={branchCls}
                              style={{ paddingLeft: 52 }}
                              onClick={() => toggleExpand(wc.id, fetchEquipmentInWorkCell)}
                            >
                              <Chevron open={expanded.has(wc.id)} />
                              <Checkbox node={{ id: wc.id, kind: "workcell", code: wc.code, name: wc.name }} />
                              <span className="text-[10px] font-mono text-gray-400 shrink-0">WC</span>
                              <span className="truncate" title={wc.name}>{wc.code}</span>
                              {loading.has(wc.id) && <Spinner />}
                            </div>

                            {expanded.has(wc.id) &&
                              ((childMap[wc.id] as Equipment[] | undefined) ?? []).map((eq) => (
                                <div
                                  key={eq.id}
                                  className={`flex items-center gap-1.5 py-1 cursor-pointer rounded ${
                                    selectedEquipmentId === eq.id
                                      ? "bg-indigo-50 text-indigo-700 font-medium"
                                      : "hover:bg-gray-100"
                                  }`}
                                  style={{ paddingLeft: 68 }}
                                  onClick={() => onSelectEquipment(eq)}
                                >
                                  <Checkbox node={{ id: eq.id, kind: "equipment", code: eq.code, name: eq.name }} />
                                  <span className="text-indigo-500 text-xs shrink-0">⚙</span>
                                  <span className="truncate" title={eq.name}>{eq.code}</span>
                                </div>
                              ))}
                          </div>
                        ))}
                    </div>
                  ))}
              </div>
            ))}
        </div>
      ))}
    </div>
  );
}
