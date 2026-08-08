import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
);

ChartJS.defaults.font.family =
  '"IBM Plex Sans", "Segoe UI", Helvetica, sans-serif';
ChartJS.defaults.font.size = 9;
ChartJS.defaults.color = "#6B6862";
