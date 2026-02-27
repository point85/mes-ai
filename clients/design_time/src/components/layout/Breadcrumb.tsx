/**
 * Breadcrumb navigation for ISA-95 hierarchy drill-down.
 */

import { Link } from "react-router-dom";
import { ChevronRightIcon, HomeIcon } from "@heroicons/react/20/solid";

export interface Crumb {
  label: string;
  to?: string; // omit for current (last) crumb
}

interface Props {
  crumbs: Crumb[];
}

export default function Breadcrumb({ crumbs }: Props) {
  return (
    <nav className="flex items-center gap-1 text-sm text-gray-500" aria-label="Breadcrumb">
      <Link to="/" className="hover:text-gray-700 transition-colors">
        <HomeIcon className="h-4 w-4" />
      </Link>
      {crumbs.map((crumb, i) => (
        <span key={i} className="flex items-center gap-1">
          <ChevronRightIcon className="h-4 w-4 text-gray-300" />
          {crumb.to ? (
            <Link to={crumb.to} className="hover:text-indigo-600 transition-colors">
              {crumb.label}
            </Link>
          ) : (
            <span className="font-medium text-gray-700">{crumb.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
