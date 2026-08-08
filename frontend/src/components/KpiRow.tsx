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
            <span className={cls(vp)}>{arrow(vp)} plan</span>
          ) : (
            <span className="mut">no plan</span>
          )}
          <span className="mut">plan {fmtMoney(kpis.plan_sales)}</span>
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
        <div className="lbl">Gross Margin</div>
        <div className="val">
          {kpis.gross_margin_pct != null
            ? `${kpis.gross_margin_pct.toFixed(1)}%`
            : "—"}
        </div>
        <div className="cmp">
          <span
            className={
              kpis.gross_margin_pct != null && kpis.gross_margin_pct < 61
                ? "down"
                : "up"
            }
          >
            {kpis.gross_margin_pct != null && kpis.gross_margin_pct < 61
              ? "below"
              : "above"}{" "}
            target
          </span>
        </div>
      </div>
      <div className="kpi">
        <div className="lbl">Full-price Sell-thru</div>
        <div className="val">
          {kpis.full_price_sell_thru_pct != null
            ? `${Math.min(kpis.full_price_sell_thru_pct, 99).toFixed(1)}%`
            : "—"}
        </div>
        <div className="cmp">
          <span className="mut">target 55%</span>
        </div>
      </div>
      <div className="kpi">
        <div className="lbl">Weeks Cover</div>
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
