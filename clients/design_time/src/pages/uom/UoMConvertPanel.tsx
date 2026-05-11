/**
 * UoM Conversion test panel — pick two units and convert a value.
 */

import { useMemo, useState } from "react";
import { useConvertUoM } from "../../hooks/useUoM";
import type { UoM, ConversionResult } from "../../types";
import { ArrowsRightLeftIcon } from "@heroicons/react/24/outline";

interface Props {
  uoms: UoM[];
}

export default function UoMConvertPanel({ uoms }: Props) {
  const [value, setValue] = useState("1");
  const [typeFilter, setTypeFilter] = useState("");
  const [fromSymbol, setFromSymbol] = useState("");
  const [toSymbol, setToSymbol] = useState("");
  const [result, setResult] = useState<ConversionResult | null>(null);

  const convertMut = useConvertUoM();

  const symbolMap = useMemo(() => new Map(uoms.map((u) => [u.symbol, u])), [uoms]);

  const uomTypes = Array.from(new Set(uoms.map((u) => u.uom_type))).sort();
  const filteredUoms = typeFilter ? uoms.filter((u) => u.uom_type === typeFilter) : uoms;

  const isRate = (u: UoM) => u.numerator_uom_symbol != null;
  // Use the pre-resolved type fields from the API — no secondary symbolMap lookup needed.
  const numType = (u: UoM) => u.numerator_uom_type ?? null;
  const denType = (u: UoM) => u.denominator_uom_type ?? null;

  const fromUom = fromSymbol ? symbolMap.get(fromSymbol) : undefined;
  const toUom = toSymbol ? symbolMap.get(toSymbol) : undefined;

  // For the To dropdown: if "from" is a rate, restrict to compatible rate units only.
  const toFilteredUoms =
    fromUom && isRate(fromUom)
      ? filteredUoms.filter(
          (u) =>
            isRate(u) &&
            numType(u) === numType(fromUom) &&
            denType(u) === denType(fromUom)
        )
      : filteredUoms;

  // Client-side validation for rate unit compatibility.
  const rateValidationError: string | null = (() => {
    if (!fromUom || !toUom) return null;
    if (!isRate(fromUom) && !isRate(toUom)) return null;
    if (isRate(fromUom) !== isRate(toUom))
      return "Both units must be rate units (e.g. kg/hr and g/min).";
    const fn = numType(fromUom);
    const tn = numType(toUom);
    const fd = denType(fromUom);
    const td = denType(toUom);
    if (fn !== tn)
      return `Numerator types must match: "${fn}" vs "${tn}".`;
    if (fd !== td)
      return `Denominator types must match: "${fd}" vs "${td}".`;
    return null;
  })();

  const handleConvert = async () => {
    if (!fromSymbol || !toSymbol || !value || rateValidationError) return;
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
        {/* Type filter */}
        <div className="w-36">
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
            {uomTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
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
        <div className="w-32">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            From
          </label>
          <select
            value={fromSymbol}
            onChange={(e) => {
              setFromSymbol(e.target.value);
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
        <div className="w-32">
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
          disabled={!fromSymbol || !toSymbol || !value || !!rateValidationError || convertMut.isPending}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-40 transition-colors"
        >
          {convertMut.isPending ? "…" : "Convert"}
        </button>
      </div>

      {/* Rate compatibility validation */}
      {rateValidationError && (
        <div className="mt-3 rounded-md bg-amber-50 px-4 py-2 text-sm text-amber-700 border border-amber-200">
          {rateValidationError}
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
            ?.detail ?? "Conversion failed — units must share the same type."}
        </div>
      )}
    </div>
  );
}
