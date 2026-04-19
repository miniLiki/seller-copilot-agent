const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = payload?.detail?.error?.message ?? payload?.detail ?? response.statusText;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export type ProductTemplate = {
  id: string;
  product_code: string;
  title: string;
  category: string;
  brand?: string;
  status: string;
};

export type Sku = {
  id: string;
  sku_code: string;
  product_template_id: string;
  title: string;
  market: string;
  price: number;
  hero_image_url: string;
  status: string;
};

export type Warehouse = {
  id: string;
  warehouse_code: string;
  name: string;
  status: string;
};

export type InventoryBalance = {
  id: string;
  sku_id: string;
  sku_code: string;
  warehouse_id: string;
  warehouse_code: string;
  on_hand: number;
  allocated: number;
  available_to_sell: number;
  inbound: number;
  damaged: number;
  quarantine: number;
  risk_level: string;
};

export type InventoryMovement = {
  id: string;
  movement_type: string;
  sku_id: string;
  warehouse_id: string;
  quantity: number;
  quantity_on_hand_delta: number;
  quantity_allocated_delta: number;
  reason?: string;
  created_at: string;
};
