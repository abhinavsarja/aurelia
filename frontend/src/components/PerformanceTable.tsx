import { arrow, cls, type DashboardFilters, type Snapshot } from "../lib/dashboard";

interface Props {
  filters: DashboardFilters;
  table: Snapshot["table"];
  week: string;
  onChange: (next: DashboardFilters) => void;
}

export function PerformanceTable({ filters, table, week, onChange }: Props) {
  const level = table.level;

  return (
    <div className="card">
      <div className="crumb">
        {filters.department === "all" ? (
          <span className="cur">All departments</span>
        ) : (
          <button
            type="button"
            onClick={() =>
              onChange({
                ...filters,
                department: "all",
                model: "all",
                sku: "all",
              })
            }
          >
            All departments
          </button>
        )}
        {filters.department !== "all" && (
          <>
            <span>›</span>
            {filters.model === "all" ? (
              <span className="cur">{filters.department}</span>
            ) : (
              <button
                type="button"
                onClick={() =>
                  onChange({ ...filters, model: "all", sku: "all" })
                }
              >
                {filters.department}
              </button>
            )}
          </>
        )}
        {filters.model !== "all" && (
          <>
            <span>›</span>
            {filters.sku === "all" ? (
              <span className="cur">{filters.model}</span>
            ) : (
              <button
                type="button"
                onClick={() => onChange({ ...filters, sku: "all" })}
              >
                {filters.model}
              </button>
            )}
          </>
        )}
        {filters.sku !== "all" && (
          <>
            <span>›</span>
            <span className="cur">{filters.sku}</span>
          </>
        )}
      </div>
      <h3>{table.title}</h3>
      <div className="sub">
        {week} · {table.rows.length}{" "}
        {level === "dept"
          ? "departments"
          : level === "model"
            ? "styles"
            : "SKUs"}{" "}
        · click a row to drill down
      </div>
      <div className="tbox">
        <table>
          <thead>
            <tr>
              {level === "sku" ? (
                <>
                  <th>SKU</th>
                  <th>Colour</th>
                  <th className="n">Units</th>
                  <th className="n">Net sales</th>
                  <th className="n">vs Plan</th>
                  <th className="n">Disc</th>
                  <th>Sell-thru</th>
                  <th className="n">Stock</th>
                </>
              ) : (
                <>
                  <th>{level === "dept" ? "Department" : "Style"}</th>
                  <th />
                  <th className="n">Units</th>
                  <th className="n">Net sales</th>
                  <th className="n">vs Plan</th>
                  <th className="n" />
                  <th>Sell-thru</th>
                  <th className="n">Stock</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((it) => (
              <tr
                key={it.key}
                className={`clk${it.low_stock ? " flag" : ""}${it.selected ? " sel" : ""}`}
                onClick={() => {
                  if (level === "dept") {
                    onChange({
                      ...filters,
                      department: it.key,
                      model: "all",
                      sku: "all",
                    });
                  } else if (level === "model") {
                    onChange({ ...filters, model: it.key, sku: "all" });
                  } else {
                    onChange({
                      ...filters,
                      sku: filters.sku === it.key ? "all" : it.key,
                    });
                  }
                }}
              >
                <td className={level === "sku" ? "sku" : undefined}>
                  {it.name}
                </td>
                <td>
                  {it.sub}
                  {it.low_stock ? <span className="chip">low stock</span> : null}
                </td>
                <td className="n">{it.units.toLocaleString()}</td>
                <td className="n">
                  S${Math.round(it.net_sales).toLocaleString()}
                </td>
                <td className={`n ${cls(it.vs_plan_pct)}`}>
                  {it.vs_plan_pct != null ? arrow(it.vs_plan_pct) : "—"}
                </td>
                <td className="n">
                  {level === "sku"
                    ? `${it.discount_pct ?? 0}%`
                    : ""}
                </td>
                <td>
                  <span className="bar">
                    <i
                      style={{
                        width: `${Math.min(it.sell_thru_pct, 100)}%`,
                      }}
                    />
                  </span>
                  {it.sell_thru_pct}%
                </td>
                <td className="n">{it.stock.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
