/**
 * TanStack Query hooks for Genealogy / Traceability.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchUnitGenealogy, fetchLotGenealogy } from "../api/genealogy";

const KEYS = {
  unitGenealogy: (unitId: string) => ["genealogy", "unit", unitId] as const,
  lotGenealogy: (lotId: string) => ["genealogy", "lot", lotId] as const,
};

export function useUnitGenealogy(unitId: string, enabled = true) {
  return useQuery({
    queryKey: KEYS.unitGenealogy(unitId),
    queryFn: () => fetchUnitGenealogy(unitId),
    enabled: !!unitId && enabled,
  });
}

export function useLotGenealogy(lotId: string, enabled = true) {
  return useQuery({
    queryKey: KEYS.lotGenealogy(lotId),
    queryFn: () => fetchLotGenealogy(lotId),
    enabled: !!lotId && enabled,
  });
}
