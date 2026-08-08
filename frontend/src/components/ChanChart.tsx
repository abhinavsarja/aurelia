import { Bar } from "react-chartjs-2";
import "./charts";

interface Props {
  labels: string[];
  stores: number[];
  ecom: number[];
}

export function ChanChart({ labels, stores, ecom }: Props) {
  return (
    <div className="card">
      <h3>Channel split</h3>
      <div className="sub">Net sales, S$'000</div>
      <div className="cbox">
        <Bar
          data={{
            labels,
            datasets: [
              {
                label: "Stores",
                data: stores,
                backgroundColor: "#1C1B19",
                borderRadius: 2,
                barThickness: 14,
              },
              {
                label: "E-comm",
                data: ecom,
                backgroundColor: "#C0A575",
                borderRadius: 2,
                barThickness: 14,
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
                  pointStyle: "rectRounded",
                  padding: 8,
                  font: { size: 9 },
                },
              },
            },
            scales: {
              x: {
                stacked: true,
                grid: { display: false },
                border: { color: "#E4E1DA" },
              },
              y: {
                stacked: true,
                grid: { color: "#F0EEE9" },
                border: { display: false },
                ticks: { maxTicksLimit: 5 },
              },
            },
          }}
        />
      </div>
    </div>
  );
}
