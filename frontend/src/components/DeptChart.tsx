import { Bar } from "react-chartjs-2";
import { fmtMoney, type Snapshot } from "../lib/dashboard";
import "./charts";

interface Props {
  weekLabel: string;
  monthLabel: string;
  values: number[];
  rows: Snapshot["dept_variance"]["rows"];
}

const HEADING_TIP =
  "For the selected week, each bar is that department’s sales versus its weekly share of the monthly target (%). " +
  "The figure next to each department is the full-month target for that department.";

export function DeptChart({ weekLabel, monthLabel, values, rows }: Props) {
  const labels = rows.map(
    (r) => `${r.department}  ·  ${fmtMoney(r.month_target)}`,
  );

  return (
    <div className="card">
      <h3 className="dept-heading">
        Department variance to target
        <span className="info-tip" title={HEADING_TIP} aria-label={HEADING_TIP}>
          ?
        </span>
      </h3>
      <div className="sub dept-month">{monthLabel}</div>
      <div className="sub mut">Week {weekLabel} · month target beside each department</div>
      <div className="cbox">
        <Bar
          data={{
            labels,
            datasets: [
              {
                data: values,
                backgroundColor: values.map((v) =>
                  v < 0 ? "rgba(180,69,60,.8)" : "rgba(46,125,91,.8)",
                ),
                borderRadius: 3,
                barThickness: 12,
              },
            ],
          }}
          options={{
            indexAxis: "y",
            maintainAspectRatio: false,
            animation: { duration: 350 },
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  title: (items) => {
                    const i = items[0]?.dataIndex ?? 0;
                    return rows[i]?.department ?? "";
                  },
                  label: (item) => {
                    const pct = Number(item.raw);
                    const sign = pct > 0 ? "+" : "";
                    return `${sign}${pct.toFixed(1)}% vs weekly target`;
                  },
                },
              },
            },
            scales: {
              x: {
                grid: { color: "#F0EEE9" },
                border: { display: false },
                ticks: {
                  maxTicksLimit: 5,
                  callback: (v) => `${v}%`,
                },
              },
              y: {
                grid: { display: false },
                border: { display: false },
                ticks: {
                  font: { size: 10 },
                  autoSkip: false,
                },
              },
            },
          }}
        />
      </div>
    </div>
  );
}
