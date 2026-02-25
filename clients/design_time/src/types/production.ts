/**
 * Production Order: TypeScript types mirroring server Pydantic schemas.
 */

export interface ProductionOrder {
  id: string;
  order_number: string;
  product_id: string;
  route_id: string | null;
  quantity_ordered: number;
  quantity_completed: number;
  quantity_scrapped: number;
  status: string;
  priority: number;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  erp_reference: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrderCreate {
  order_number: string;
  product_id: string;
  route_id?: string | null;
  quantity_ordered: number;
  priority?: number;
  planned_start?: string | null;
  planned_end?: string | null;
  erp_reference?: string | null;
  notes?: string | null;
}

export interface OrderUpdate {
  order_number?: string;
  product_id?: string;
  route_id?: string | null;
  quantity_ordered?: number;
  priority?: number;
  planned_start?: string | null;
  planned_end?: string | null;
  erp_reference?: string | null;
  notes?: string | null;
}
