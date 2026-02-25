/**
 * UoM Conversion test panel — pick two units and convert a value.
 */

import { useState } from "react";
import { useConvertUoM } from "../../hooks/useUoM";
import type { UoM, ConversionResult } from "../../types";
import { ArrowsRightLeftIcon } from "@heroicons/react/24/outline";

interface Props {
  uoms: UoM[];
}

export default function UoMConvertPanel({ uoms }: Props) {
  const [value, setValue] = useState("1");
  const [fromSymbol, setFromSymbol] = useState("");
  const [toSymbol, setToSymbol] = useState("");
  const [result, setResult] = useState<ConversionResult | null>(null);

  const convertMut = useConvertUoM();

  const handleConvert = async () => {
    if (!fromSymbol || !toSymbol || !value) return;
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
            {uoms.map((u) => (
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
            {uoms.map((u) => (
              <option key={u.id} value={u.symbol}>
                {u.symbol} ({u.name})
              </option>
            ))}
          </select>
        </div>

        {/* Convert button */}
        <button
          onClick={handleConvert}
          disabled={!fromSymbol || !toSymbol || !value || convertMut.isPending}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-40 transition-colors"
        >
          {convertMut.isPending ? "…" : "Convert"}
        </button>
      </div>

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
