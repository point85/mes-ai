import { useState, useEffect } from "react";
import {
  fetchSites,
  fetchAreas,
  fetchLines,
  fetchWorkCells,
  fetchEquipmentInWorkCell,
} from "../api/endpoints";
import type { Area, ProductionLine, WorkCell, Equipment } from "../types";

interface EquipmentTreeProps {
  selectedEquipmentId: string | null;
  onSelectEquipment: (id: string, code: string, name: string) => void;
}

export default function EquipmentTree({
  selectedEquipmentId,
  onSelectEquipment,
}: EquipmentTreeProps) {
  const [sites, setSites] = useState<{ id: string; code: string; name: string }[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [childMap, setChildMap] = useState<Record<string, (Area | ProductionLine | WorkCell | Equipment)[]>>({});
  const [loading, setLoading] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchSites().then(setSites).catch(() => {});
  }, []);

  async function toggleNode(
    id: string,
    fetcher: (parentId: string) => Promise<(Area | ProductionLine | WorkCell | Equipment)[]>,
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

  const Spinner = () => <span className="text-[10px] text-gray-400 animate-pulse ml-auto">…</span>;

  const branchClass =
    "flex items-center gap-1.5 py-1 cursor-pointer rounded hover:bg-gray-100";

  return (
    <div className="text-sm select-none">
      {sites.length === 0 && (
        <p className="px-2 py-3 text-xs text-gray-400">Loading sites…</p>
      )}
      {sites.map((site) => (
        <div key={site.id}>
          {/* Site */}
          <div
            className={branchClass}
            style={{ paddingLeft: 4 }}
            onClick={() => toggleNode(site.id, fetchAreas)}
          >
            <Chevron open={expanded.has(site.id)} />
            <span className="text-[10px] font-mono text-gray-400 shrink-0">S</span>
            <span className="truncate" title={site.name}>{site.code}</span>
            {loading.has(site.id) && <Spinner />}
          </div>

          {expanded.has(site.id) &&
            ((childMap[site.id] as Area[] | undefined) ?? []).map((area) => (
              <div key={area.id}>
                {/* Area */}
                <div
                  className={branchClass}
                  style={{ paddingLeft: 20 }}
                  onClick={() => toggleNode(area.id, fetchLines)}
                >
                  <Chevron open={expanded.has(area.id)} />
                  <span className="text-[10px] font-mono text-gray-400 shrink-0">A</span>
                  <span className="truncate" title={area.name}>{area.code}</span>
                  {loading.has(area.id) && <Spinner />}
                </div>

                {expanded.has(area.id) &&
                  ((childMap[area.id] as ProductionLine[] | undefined) ?? []).map((line) => (
                    <div key={line.id}>
                      {/* Line */}
                      <div
                        className={branchClass}
                        style={{ paddingLeft: 36 }}
                        onClick={() => toggleNode(line.id, fetchWorkCells)}
                      >
                        <Chevron open={expanded.has(line.id)} />
                        <span className="text-[10px] font-mono text-gray-400 shrink-0">L</span>
                        <span className="truncate" title={line.name}>{line.code}</span>
                        {loading.has(line.id) && <Spinner />}
                      </div>

                      {expanded.has(line.id) &&
                        ((childMap[line.id] as WorkCell[] | undefined) ?? []).map((wc) => (
                          <div key={wc.id}>
                            {/* Work Cell */}
                            <div
                              className={branchClass}
                              style={{ paddingLeft: 52 }}
                              onClick={() => toggleNode(wc.id, fetchEquipmentInWorkCell)}
                            >
                              <Chevron open={expanded.has(wc.id)} />
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
                                      ? "bg-emerald-50 text-emerald-700 font-medium"
                                      : "hover:bg-gray-100"
                                  }`}
                                  style={{ paddingLeft: 72 }}
                                  onClick={() => onSelectEquipment(eq.id, eq.code, eq.name)}
                                >
                                  <span className="text-emerald-500 text-xs shrink-0">⚙</span>
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
