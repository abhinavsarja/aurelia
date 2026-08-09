import { Line } from "react-chartjs-2";
import "./charts";

interface Props {
  title: string;
  sub: string;
  labels: string[];
  actual: number[];
  plan: number[];
  highlightIndex: number;
}

export function TrendChart({
  title,
  sub,
  labels,
  actual,
  plan,
  highlightIndex,
}: Props) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="sub">{sub}</div>
      <div className="cbox">
        <Line
          data={{
            labels,
            datasets: [
              {
                label: "Actual",
                data: actual,
                borderColor: "#1C1B19",
                backgroundColor: "rgba(28,27,25,.05)",
                borderWidth: 2,
                tension: 0.32,
                fill: true,
                pointRadius: actual.map((_, i) =>
                  i === highlightIndex ? 4 : 0,
                ),
                pointBackgroundColor: "#1C1B19",
              },
              {
                label: "Target",
                data: plan,
                borderColor: "#8A6D3B",
                borderWidth: 1.4,
                borderDash: [5, 4],
                tension: 0.32,
                fill: false,
                pointRadius: 0,
              },
            ],
          }}
          options={{
            maintainAspectRatio: false,
            animation: { duration: 350 },
            plugins: {
              legend: {
                position: "top",
                align: "end",
                labels: {
                  boxWidth: 8,
                  boxHeight: 8,
                  usePointStyle: true,
                  pointStyle: "line",
                  padding: 10,
                  font: { size: 9 },
                },
              },
            },
            scales: {
              y: {
                grid: { color: "#F0EEE9" },
                border: { display: false },
                ticks: {
                  maxTicksLimit: 5,
                  callback: (v) =>
                    Number(v) >= 1000
                      ? `${(Number(v) / 1000).toFixed(1)}m`
                      : `${v}k`,
                },
              },
              x: {
                grid: { display: false },
                border: { color: "#E4E1DA" },
              },
            },
          }}
        />
      </div>
    </div>
  );
}
