/**
 * Route Flow Diagram — renders a route's steps + transitions as a
 * Mermaid directed graph.  Colors edges by transition condition:
 *   - always / on_pass   → green
 *   - on_fail            → red
 *   - on_rework          → amber
 *   - disposition        → blue
 *
 * Useful for verifying rework loops, MRB escalations, and branching logic.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import mermaid from "mermaid";
import { fetchStepTransitions } from "../../api/productDef";
import type { RouteStep } from "../../types";

interface Props {
  steps: RouteStep[];
}

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  flowchart: { htmlLabels: true, curve: "basis" },
  securityLevel: "loose",
});

const CONDITION_STYLE: Record<string, { color: string; label: string }> = {
  always: { color: "#16a34a", label: "always" },
  on_pass: { color: "#16a34a", label: "on_pass" },
  on_fail: { color: "#dc2626", label: "on_fail" },
  on_rework: { color: "#d97706", label: "on_rework" },
  disposition: { color: "#2563eb", label: "disposition" },
};

function sanitize(text: string): string {
  return text.replace(/"/g, "&quot;").replace(/\n/g, " ");
}

function stepNode(s: RouteStep): string {
  const shape: Record<string, [string, string]> = {
    production: ["[", "]"],
    inspection: ["{{", "}}"],
    rework: ["([", "])"],
    mrb: ["[[", "]]"],
  };
  const [open, close] = shape[s.step_type] ?? shape.production;
  const label = `${s.sequence}. ${sanitize(s.name)}`;
  return `step_${s.id.replace(/-/g, "")}${open}"${label}"${close}`;
}

function stepId(s: RouteStep): string {
  return `step_${s.id.replace(/-/g, "")}`;
}

export default function RouteFlowDiagram({ steps }: Props) {
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const transitionQueries = useQueries({
    queries: steps.map((s) => ({
      queryKey: ["stepTransitions", s.id],
      queryFn: () => fetchStepTransitions(s.id),
      enabled: !!s.id,
    })),
  });

  const allLoaded = transitionQueries.every((q) => !q.isLoading);
  const allTransitions = useMemo(
    () => transitionQueries.flatMap((q) => q.data?.data ?? []),
    [transitionQueries],
  );

  const markup = useMemo(() => {
    if (steps.length === 0) return "";
    const lines: string[] = ["flowchart TD"];
    const stepByIdMap = new Map(steps.map((s) => [s.id, s]));

    // node definitions (sorted by sequence)
    const sortedSteps = [...steps].sort((a, b) => a.sequence - b.sequence);
    for (const s of sortedSteps) {
      lines.push(`  ${stepNode(s)}`);
    }

    // class styling per step_type
    const classOf: Record<string, string> = {
      production: "prod",
      inspection: "insp",
      rework: "rework",
      mrb: "mrb",
    };
    for (const s of sortedSteps) {
      lines.push(`  class ${stepId(s)} ${classOf[s.step_type] ?? "prod"}`);
    }
    lines.push("  classDef prod fill:#e0e7ff,stroke:#4f46e5,color:#1e1b4b");
    lines.push("  classDef insp fill:#fef3c7,stroke:#d97706,color:#78350f");
    lines.push("  classDef rework fill:#fee2e2,stroke:#dc2626,color:#7f1d1d");
    lines.push("  classDef mrb fill:#ede9fe,stroke:#7c3aed,color:#4c1d95");

    // edges
    let edgeIdx = 0;
    const edgeStyles: string[] = [];
    for (const t of allTransitions) {
      const from = stepByIdMap.get(t.from_step_id);
      const to = stepByIdMap.get(t.to_step_id);
      if (!from || !to) continue;
      const style = CONDITION_STYLE[t.condition] ?? { color: "#6b7280", label: t.condition };
      const edgeLabel = t.label ? `${style.label}: ${sanitize(t.label)}` : style.label;
      lines.push(`  ${stepId(from)} -- "${edgeLabel}" --> ${stepId(to)}`);
      edgeStyles.push(`  linkStyle ${edgeIdx} stroke:${style.color},stroke-width:2px`);
      edgeIdx += 1;
    }
    lines.push(...edgeStyles);

    return lines.join("\n");
  }, [steps, allTransitions]);

  useEffect(() => {
    if (!allLoaded || !markup) {
      setSvg("");
      return;
    }
    let cancelled = false;
    const id = `route-diagram-${Date.now()}`;
    mermaid
      .render(id, markup)
      .then(({ svg }) => {
        if (!cancelled) {
          setSvg(svg);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setSvg("");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [markup, allLoaded]);

  if (steps.length === 0) {
    return (
      <p className="p-6 text-sm text-gray-500">
        No steps defined — add steps to see the flow diagram.
      </p>
    );
  }

  if (!allLoaded) {
    return <p className="p-6 text-sm text-gray-500">Loading transitions…</p>;
  }

  return (
    <div className="space-y-3 p-4">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="font-semibold text-gray-700">Edge colors:</span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-5 bg-green-600" /> always / on_pass
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-5 bg-red-600" /> on_fail
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-5 bg-amber-600" /> on_rework
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-5 bg-blue-600" /> disposition
        </span>
      </div>
      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          <p className="font-semibold">Diagram render error</p>
          <pre className="whitespace-pre-wrap">{error}</pre>
          <details className="mt-2">
            <summary className="cursor-pointer">Show Mermaid source</summary>
            <pre className="mt-2 overflow-x-auto rounded bg-white p-2">{markup}</pre>
          </details>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="overflow-x-auto rounded border border-gray-200 bg-white p-3"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      )}
    </div>
  );
}
