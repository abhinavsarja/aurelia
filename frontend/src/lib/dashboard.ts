const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface CatalogSku {
  sku: string;
  colour: string;
}

export interface CatalogModel {
  name: string;
  skus: CatalogSku[];
}

export interface CatalogDept {
  name: string;
  models: CatalogModel[];
}

export interface Catalog {
  weeks: string[];
  channels: string[];
  departments: CatalogDept[];
  latest_week: string;
}

export interface DashboardFilters {
  week: string;
  department: string;
  model: string;
  sku: string;
  channel: string;
}

export interface Snapshot {
  week: string;
  scope_label: string;
  channel: string;
  channel_label: string;
  filters: {
    department: string;
    model: string;
    sku: string;
    channel: string;
  };
  kpis: {
    net_sales: number;
    units: number;
    plan_sales: number;
    vs_plan_pct: number | null;
    month_target: number;
    month_label: string;
    stock_units: number;
    weeks_cover: number | null;
  };
  trend: {
    labels: string[];
    actual: number[];
    plan: number[];
    highlight_index: number;
  };
  dept_variance: {
    week: string;
    month: string;
    month_label: string;
    labels: string[];
    values: number[];
    rows: {
      department: string;
      variance_pct: number;
      actual: number;
      week_target: number;
      month_target: number;
    }[];
  };
  channel_split: { labels: string[]; stores: number[]; ecom: number[] };
  table: {
    level: "dept" | "model" | "sku";
    title: string;
    rows: {
      key: string;
      name: string;
      sub: string;
      units: number;
      net_sales: number;
      vs_plan_pct: number | null;
      discount_pct: number | null;
      sell_thru_pct: number;
      stock: number;
      low_stock: boolean;
      selected: boolean;
    }[];
  };
}

function qs(filters: DashboardFilters): string {
  const p = new URLSearchParams();
  p.set("week", filters.week);
  p.set("channel", filters.channel);
  if (filters.department && filters.department !== "all") {
    p.set("department", filters.department);
  }
  if (filters.model && filters.model !== "all") {
    p.set("model", filters.model);
  }
  if (filters.sku && filters.sku !== "all") {
    p.set("sku", filters.sku);
  }
  return p.toString();
}

export async function fetchCatalog(): Promise<Catalog> {
  const res = await fetch(`${API_BASE}/dashboard/catalog`);
  if (!res.ok) throw new Error(`catalog ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function fetchSnapshot(filters: DashboardFilters): Promise<Snapshot> {
  const res = await fetch(`${API_BASE}/dashboard/snapshot?${qs(filters)}`);
  if (!res.ok) throw new Error(`snapshot ${res.status}: ${await res.text()}`);
  return res.json();
}

export function fmtMoney(v: number) {
  return v >= 1e6 ? `S$${(v / 1e6).toFixed(2)}m` : `S$${Math.round(v / 1000)}k`;
}

export function arrow(v: number) {
  return `${v < 0 ? "▼ " : "▲ "}${Math.abs(v).toFixed(1)}%`;
}

export function cls(v: number | null | undefined) {
  if (v == null) return "mut";
  return v < 0 ? "down" : "up";
}
