/**
 * Route Flow Diagram — renders a route's steps + disposition edges as a
 * Mermaid directed graph.
 *
 * Edges are derived from the steps' input/output disposition lists:
 * a step's output disposition becomes an edge to every step whose input
 * list contains the same disposition. Edges are labeled with the
 * disposition code.
 *
 * The optional `validation` prop is used purely as a status banner —
 * the graph is always rendered, but invalid routes are highlighted so
 * the user knows the diagram may show dangling/orphan edges.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import mermaid from "mermaid";
import type { RouteStep, RouteValidationResult } from "../../types";

interface Props {
  steps: RouteStep[];
  validation?: RouteValidationResult | null;
}

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  flowchart: { htmlLabels: true, curve: "basis" },
  securityLevel: "loose",
});

function sanitize(text: string): string {
  return text.replace(/"/g, "&quot;").replace(/\n/g, " ");
}

function nodeId(s: RouteStep): string {
  return `step_${s.id.replace(/-/g, "")}`;
}

function stepNode(s: RouteStep): string {
  const shape: Record<string, [string, string]> = {
    production: ["[", "]"],
    inspection: ["{{", "}}"],
    rework: ["([", "])"],
    mrb: ["[[", "]]"],
  };
  const [open, close] = shape[s.step_type] ?? shape.production;
  const initialMark = s.is_initial_step ? "● " : "";
  const label = `${initialMark}${s.sequence}. ${sanitize(s.name)}`;
  return `${nodeId(s)}${open}"${label}"${close}`;
}

export default function RouteFlowDiagram({ steps, validation }: Props) {
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const markup = useMemo(() => {
    if (steps.length === 0) return "";
    const lines: string[] = ["flowchart TD"];

    const sortedSteps = [...steps].sort((a, b) => a.sequence - b.sequence);
    for (const s of sortedSteps) {
      lines.push(`  ${stepNode(s)}`);
    }

    const classOf: Record<string, string> = {
      production: "prod",
      inspection: "insp",
      rework: "rework",
      mrb: "mrb",
    };
    for (const s of sortedSteps) {
      lines.push(`  class ${nodeId(s)} ${classOf[s.step_type] ?? "prod"}`);
    }
    lines.push("  classDef prod fill:#e0e7ff,stroke:#4f46e5,color:#1e1b4b");
    lines.push("  classDef insp fill:#fef3c7,stroke:#d97706,color:#78350f");
    lines.push("  classDef rework fill:#fee2e2,stroke:#dc2626,color:#7f1d1d");
    lines.push("  classDef mrb fill:#ede9fe,stroke:#7c3aed,color:#4c1d95");

    // Build an index from disposition id → steps that consume it as an
    // input. Each output disposition then produces an edge to every
    // consumer step, so shared sinks render as fan-in correctly.
    const consumers = new Map<string, RouteStep[]>();
    for (const s of sortedSteps) {
      for (const d of s.input_dispositions ?? []) {
        const arr = consumers.get(d.id) ?? [];
        arr.push(s);
        consumers.set(d.id, arr);
      }
    }

    for (const src of sortedSteps) {
      for (const d of src.output_dispositions ?? []) {
        const targets = consumers.get(d.id) ?? [];
        if (targets.length === 0) {
          const ghost = `ghost_${d.id.replace(/-/g, "")}`;
          lines.push(`  ${ghost}(["⚠ ${sanitize(d.code)}<br/>(unconsumed)"])`);
          lines.push(`  class ${ghost} ghost`);
          lines.push(`  ${nodeId(src)} -- "${sanitize(d.code)}" --> ${ghost}`);
          continue;
        }
        for (const tgt of targets) {
          lines.push(
            `  ${nodeId(src)} -- "${sanitize(d.code)}" --> ${nodeId(tgt)}`,
          );
        }
      }
    }
    lines.push(
      "  classDef ghost fill:#fef2f2,stroke:#dc2626,color:#7f1d1d,stroke-dasharray: 4 2",
    );

    return lines.join("\n");
  }, [steps]);

  useEffect(() => {
    if (!markup) {
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
  }, [markup]);

  if (steps.length === 0) {
    return (
      <p className="p-6 text-sm text-gray-500">
        No steps defined — add steps to see the flow diagram.
      </p>
    );
  }

  return (
    <div className="space-y-3 p-4">
      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600">
        <span className="font-semibold text-gray-700">Legend:</span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded bg-indigo-100 ring-1 ring-indigo-500" /> production
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded bg-amber-100 ring-1 ring-amber-500" /> inspection
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded bg-red-100 ring-1 ring-red-500" /> rework
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded bg-violet-100 ring-1 ring-violet-500" /> mrb
        </span>
        <span className="text-gray-500">●&nbsp;= initial step</span>
        <span className="text-gray-500">edges labeled by disposition code</span>
      </div>
      {validation && !validation.valid && (
        <div className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
          Diagram may include dangling or orphan edges — see the validation
          panel above for details.
        </div>
      )}
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
