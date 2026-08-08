import type { Catalog, DashboardFilters } from "../lib/dashboard";

interface Props {
  catalog: Catalog;
  filters: DashboardFilters;
  onChange: (next: DashboardFilters) => void;
  onReset: () => void;
}

export function TopBar({ catalog, filters, onChange, onReset }: Props) {
  const dept = catalog.departments.find((d) => d.name === filters.department);
  const models = dept?.models ?? [];
  const model = models.find((m) => m.name === filters.model);
  const skus = model?.skus ?? [];

  // show latest weeks first in the dropdown
  const weeksDesc = [...catalog.weeks].reverse();

  return (
    <header className="topbar">
      <div className="brand">
        <h1>AURELIA</h1>
        <span>Accessories · Singapore</span>
      </div>
      <div className="controls">
        <div className="fl">
          <label>Week</label>
          <select
            className="sel"
            value={filters.week}
            onChange={(e) => onChange({ ...filters, week: e.target.value })}
          >
            {weeksDesc.map((w) => (
              <option key={w} value={w}>
                {w}
              </option>
            ))}
          </select>
        </div>
        <div className="fl">
          <label>Department</label>
          <select
            className={`sel${filters.department !== "all" ? " on" : ""}`}
            value={filters.department}
            onChange={(e) =>
              onChange({
                ...filters,
                department: e.target.value,
                model: "all",
                sku: "all",
              })
            }
          >
            <option value="all">All departments</option>
            {catalog.departments.map((d) => (
              <option key={d.name} value={d.name}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div className="fl">
          <label>Style / Model</label>
          <select
            className={`sel${filters.model !== "all" ? " on" : ""}`}
            value={filters.model}
            disabled={filters.department === "all"}
            onChange={(e) =>
              onChange({ ...filters, model: e.target.value, sku: "all" })
            }
          >
            <option value="all">
              {filters.department === "all"
                ? "— select department —"
                : "All styles"}
            </option>
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <div className="fl">
          <label>SKU</label>
          <select
            className={`sel${filters.sku !== "all" ? " on" : ""}`}
            value={filters.sku}
            disabled={filters.department === "all" || filters.model === "all"}
            onChange={(e) => onChange({ ...filters, sku: e.target.value })}
          >
            <option value="all">
              {filters.model === "all" ? "— select style —" : "All SKUs"}
            </option>
            {skus.map((o) => (
              <option key={o.sku} value={o.sku}>
                {o.sku}
                {o.colour ? ` · ${o.colour}` : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="fl">
          <label>Channel</label>
          <select
            className={`sel${filters.channel !== "all" ? " on" : ""}`}
            value={filters.channel}
            onChange={(e) => onChange({ ...filters, channel: e.target.value })}
          >
            <option value="all">All channels</option>
            <option value="store">Retail stores</option>
            <option value="ecom">E-commerce</option>
          </select>
        </div>
        <button type="button" className="rst" onClick={onReset}>
          Reset
        </button>
      </div>
    </header>
  );
}
