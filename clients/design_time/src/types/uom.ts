/**
 * UOM: TypeScript types mirroring server Pydantic schemas.
 */

export interface UoM {
  id: string;
  symbol: string;
  name: string;
  description: string | null;
  uom_type: string;
  multiplier: number;
  offset: number;
  is_builtin: boolean;
  is_active: boolean;
  numerator_uom_id: string | null;
  denominator_uom_id: string | null;
  numerator_uom_symbol: string | null;
  denominator_uom_symbol: string | null;
  numerator_uom_type: string | null;
  denominator_uom_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface UoMCreate {
  symbol: string;
  name: string;
  description?: string | null;
  uom_type: string;
  multiplier: number;
  offset: number;
  numerator_uom_symbol?: string | null;
  denominator_uom_symbol?: string | null;
}

export interface UoMUpdate {
  symbol?: string;
  name?: string;
  description?: string | null;
  uom_type?: string;
  multiplier?: number;
  offset?: number;
  numerator_uom_symbol?: string | null;
  denominator_uom_symbol?: string | null;
}

export interface ConversionRequest {
  value: number;
  from_symbol: string;
  to_symbol: string;
}

export interface ConversionResult {
  original_value: number;
  from_symbol: string;
  from_name: string;
  converted_value: number;
  to_symbol: string;
  to_name: string;
}

/** Standard API envelope for a single item */
export interface ApiResponse<T> {
  status: "success";
  data: T;
}

/** Standard API envelope for lists */
export interface ApiListResponse<T> {
  status: "success";
  data: T[];
  pagination: {
    cursor: string | null;
    limit: number;
    has_more: boolean;
  };
}
