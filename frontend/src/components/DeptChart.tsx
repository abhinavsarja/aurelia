import { Bar } from "react-chartjs-2";
import "./charts";

interface Props {
  weekLabel: string;
  labels: string[];
  values: number[];
}

export function DeptChart({ weekLabel, labels, values }: Props) {
  return (
    <div className="card">
      <h3>Department variance to target</h3>
      <div className="sub">{weekLabel}</div>
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
            plugins: { legend: { display: false } },
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
              },
            },
          }}
        />
      </div>
    </div>
  );
}
