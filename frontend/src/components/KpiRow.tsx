import { arrow, cls, fmtMoney, type Snapshot } from "../lib/dashboard";

interface Props {
  kpis: Snapshot["kpis"];
}

export function KpiRow({ kpis }: Props) {
  const vp = kpis.vs_plan_pct;
  return (
    <div className="kpis">
      <div className="kpi">
        <div className="lbl">Net Sales</div>
        <div className="val">{fmtMoney(kpis.net_sales)}</div>
        <div className="cmp">
          {vp != null ? (
            <span className={cls(vp)}>{arrow(vp)} target</span>
          ) : (
            <span className="mut">no target</span>
          )}
          <span className="mut">target {fmtMoney(kpis.plan_sales)}</span>
        </div>
      </div>
      <div className="kpi">
        <div className="lbl">Units</div>
        <div className="val">{kpis.units.toLocaleString()}</div>
        <div className="cmp">
          <span className="mut">
            stock {kpis.stock_units.toLocaleString()}
          </span>
        </div>
      </div>
      <div className="kpi">
        <div className="lbl">Month target</div>
        <div className="val">{fmtMoney(kpis.month_target)}</div>
        <div className="cmp">
          <span className="mut">{kpis.month_label}</span>
        </div>
      </div>
      <div className="kpi">
        <div className="lbl">Stock cover (in weeks)</div>
        <div className="val">
          {kpis.weeks_cover != null ? kpis.weeks_cover.toFixed(1) : "—"}
        </div>
        <div className="cmp">
          <span
            className={
              kpis.weeks_cover != null &&
              (kpis.weeks_cover > 10 || kpis.weeks_cover < 4)
                ? "down"
                : "mut"
            }
          >
            target 8–10
          </span>
        </div>
      </div>
    </div>
  );
}
