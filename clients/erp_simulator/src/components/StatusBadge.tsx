interface StatusBadgeProps {
  ok: boolean;
  trueLabel?: string;
  falseLabel?: string;
}

export default function StatusBadge({
  ok,
  trueLabel = "Healthy",
  falseLabel = "Unavailable",
}: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        ok
          ? "bg-green-100 text-green-800"
          : "bg-red-100 text-red-800"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`} />
      {ok ? trueLabel : falseLabel}
    </span>
  );
}
