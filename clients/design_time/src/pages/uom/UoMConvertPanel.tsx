/**
 * UoM Conversion test panel — pick two units and convert a value.
 *
 * Filtering logic:
 *   scalar   → To dropdown shows scalars with same uom_type
 *   quotient → To dropdown shows quotients where left_uom_type AND right_uom_type match
 *   product  → same as quotient
 *   power    → To dropdown shows powers where left_uom_type AND exponent match
 */

import { useMemo, useState } from "react";
import { useConvertUoM } from "../../hooks/useUoM";
import type { UoM, ConversionResult } from "../../types";
import { UOM_TYPES } from "../../types";
import { ArrowsRightLeftIcon } from "@heroicons/react/24/outline";

const TYPE_LABELS: Record<string, string> = {
  mass: "Mass",
  length: "Length",
  time: "Time",
  temperature: "Temperature",
  other: "Other",
};

interface Props {
  uoms: UoM[];
}

function compatibilityError(from: UoM, to: UoM): string | null {
  if (from.uom_class !== to.uom_class)
    return `Class mismatch: "${from.uom_class}" vs "${to.uom_class}".`;

  const cls = from.uom_class;

  if (cls === "scalar") {
    if (from.uom_type !== to.uom_type)
      return `Type mismatch: "${from.uom_type}" vs "${to.uom_type}".`;
  } else if (cls === "quotient" || cls === "product") {
    if (from.left_uom_type !== to.left_uom_type)
      return `Left (numerator) type mismatch: "${from.left_uom_type}" vs "${to.left_uom_type}".`;
    if (from.right_uom_type !== to.right_uom_type)
      return `Right (denominator) type mismatch: "${from.right_uom_type}" vs "${to.right_uom_type}".`;
  } else if (cls === "power") {
    if (from.left_uom_type !== to.left_uom_type)
      return `Base type mismatch: "${from.left_uom_type}" vs "${to.left_uom_type}".`;
    if (from.exponent !== to.exponent)
      return `Exponent mismatch: ${from.exponent} vs ${to.exponent}.`;
  }
  return null;
}

function compatibleTo(uoms: UoM[], from: UoM): UoM[] {
  const cls = from.uom_class;
  return uoms.filter((u) => {
    if (u.uom_class !== cls) return false;
    if (cls === "scalar") return u.uom_type === from.uom_type;
    if (cls === "quotient" || cls === "product")
      return u.left_uom_type === from.left_uom_type && u.right_uom_type === from.right_uom_type;
    if (cls === "power")
      return u.left_uom_type === from.left_uom_type && u.exponent === from.exponent;
    return true;
  });
}

export default function UoMConvertPanel({ uoms }: Props) {
  const [value, setValue] = useState("1");
  const [typeFilter, setTypeFilter] = useState("");
  const [fromSymbol, setFromSymbol] = useState("");
  const [toSymbol, setToSymbol] = useState("");
  const [result, setResult] = useState<ConversionResult | null>(null);

  const convertMut = useConvertUoM();

  const symbolMap = useMemo(() => new Map(uoms.map((u) => [u.symbol, u])), [uoms]);

  // Filter From list by selected type (for scalar units, use uom_type; for composite, use left_uom_type)
  const filteredUoms = useMemo(() => {
    if (!typeFilter) return uoms;
    return uoms.filter(
      (u) => u.uom_type === typeFilter || u.left_uom_type === typeFilter,
    );
  }, [uoms, typeFilter]);

  const fromUom = fromSymbol ? symbolMap.get(fromSymbol) : undefined;
  const toUom = toSymbol ? symbolMap.get(toSymbol) : undefined;

  // To dropdown — restricted to compatible units when From is selected
  const toFilteredUoms = useMemo(
    () => (fromUom ? compatibleTo(uoms, fromUom) : filteredUoms),
    [uoms, fromUom, filteredUoms],
  );

  const validationError = fromUom && toUom ? compatibilityError(fromUom, toUom) : null;

  const handleConvert = async () => {
    if (!fromSymbol || !toSymbol || !value || validationError) return;
    try {
      const res = await convertMut.mutateAsync({
        value: parseFloat(value),
        from_symbol: fromSymbol,
        to_symbol: toSymbol,
      });
      setResult(res);
    } catch {
      setResult(null);
    }
  };

  const swap = () => {
    setFromSymbol(toSymbol);
    setToSymbol(fromSymbol);
    setResult(null);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-3">
        Conversion Test
      </h2>

      <div className="flex items-end gap-3 flex-wrap">
        {/* Type filter — fixed 5 types */}
        <div className="w-40">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setFromSymbol("");
              setToSymbol("");
              setResult(null);
            }}
            className="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All types</option>
            {UOM_TYPES.map((t) => (
              <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>
            ))}
          </select>
        </div>

        {/* Value */}
        <div className="w-28">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Value
          </label>
          <input
            type="number"
            step="any"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setResult(null);
            }}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* From */}
        <div className="w-40">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            From
          </label>
          <select
            value={fromSymbol}
            onChange={(e) => {
              setFromSymbol(e.target.value);
              setToSymbol("");
              setResult(null);
            }}
            className="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">—</option>
            {filteredUoms.map((u) => (
              <option key={u.id} value={u.symbol}>
                {u.symbol} ({u.name})
              </option>
            ))}
          </select>
        </div>

        {/* Swap button */}
        <button
          onClick={swap}
          className="rounded-md border border-gray-300 bg-white p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          title="Swap units"
        >
          <ArrowsRightLeftIcon className="h-4 w-4" />
        </button>

        {/* To */}
        <div className="w-40">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            To
          </label>
          <select
            value={toSymbol}
            onChange={(e) => {
              setToSymbol(e.target.value);
              setResult(null);
            }}
            className="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">—</option>
            {toFilteredUoms.map((u) => (
              <option key={u.id} value={u.symbol}>
                {u.symbol} ({u.name})
              </option>
            ))}
          </select>
        </div>

        {/* Convert button */}
        <button
          onClick={handleConvert}
          disabled={!fromSymbol || !toSymbol || !value || !!validationError || convertMut.isPending}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-40 transition-colors"
        >
          {convertMut.isPending ? "…" : "Convert"}
        </button>
      </div>

      {/* Compatibility validation warning */}
      {validationError && (
        <div className="mt-3 rounded-md bg-amber-50 px-4 py-2 text-sm text-amber-700 border border-amber-200">
          {validationError}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="mt-3 rounded-md bg-white border border-gray-200 px-4 py-2.5 text-sm">
          <span className="font-mono font-medium text-gray-900">
            {result.original_value} {result.from_symbol}
          </span>
          <span className="mx-2 text-gray-400">=</span>
          <span className="font-mono font-medium text-indigo-700">
            {result.converted_value} {result.to_symbol}
          </span>
          <span className="ml-2 text-xs text-gray-400">
            ({result.from_name} → {result.to_name})
          </span>
        </div>
      )}

      {/* Error */}
      {convertMut.error && (
        <div className="mt-3 rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">
          {(convertMut.error as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ?? "Conversion failed — units must share the same type and class."}
        </div>
      )}
    </div>
  );
}


    </div>
  );
}
