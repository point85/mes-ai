/**
 * UOM: TypeScript types mirroring server Pydantic schemas.
 *
 * Five types: mass, length, time, temperature, other
 * Four classes: scalar, quotient, product, power
 */

export type UoMClass = "scalar" | "quotient" | "product" | "power";
export type UoMType = "mass" | "length" | "time" | "temperature" | "electrical" | "amount_of_substance" | "luminous_intensity" | "other";

export const UOM_TYPES: UoMType[] = ["mass", "length", "time", "temperature", "electrical", "amount_of_substance", "luminous_intensity", "other"];
export const UOM_CLASSES: UoMClass[] = ["scalar", "quotient", "product", "power"];

export interface UoM {
  id: string;
  symbol: string;
  name: string;
  description: string | null;
  uom_type: string;
  uom_class: UoMClass;
  multiplier: number;
  offset: number;
  is_builtin: boolean;
  is_active: boolean;
  // Composite component IDs
  left_uom_id: string | null;
  right_uom_id: string | null;
  // Convenience read-only fields (resolved by server)
  left_uom_symbol: string | null;
  right_uom_symbol: string | null;
  left_uom_type: string | null;
  right_uom_type: string | null;
  exponent: number | null;
  created_at: string;
  updated_at: string;
}

export interface UoMCreate {
  symbol: string;
  name: string;
  description?: string | null;
  uom_type: string;
  uom_class: UoMClass;
  multiplier: number;
  offset: number;
  left_uom_symbol?: string | null;
  right_uom_symbol?: string | null;
  exponent?: number | null;
}

export interface UoMUpdate {
  symbol?: string;
  name?: string;
  description?: string | null;
  uom_type?: string;
  uom_class?: UoMClass;
  multiplier?: number;
  offset?: number;
  left_uom_symbol?: string | null;
  right_uom_symbol?: string | null;
  exponent?: number | null;
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
