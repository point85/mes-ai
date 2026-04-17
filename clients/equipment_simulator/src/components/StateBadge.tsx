const categoryColors: Record<string, string> = {
  available: "bg-green-100 text-green-800",
  busy: "bg-blue-100 text-blue-800",
  unavailable_planned: "bg-yellow-100 text-yellow-800",
  unavailable_unplanned: "bg-red-100 text-red-800",
};

interface StateBadgeProps {
  category: string;
  label?: string;
}

export default function StateBadge({ category, label }: StateBadgeProps) {
  const cls = categoryColors[category] ?? "bg-gray-100 text-gray-800";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {label ?? category}
    </span>
  );
}
