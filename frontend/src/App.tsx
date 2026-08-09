import { useEffect, useState } from "react";
import { ChanChart } from "./components/ChanChart";
import { ChatPanel } from "./components/ChatPanel";
import { DeptChart } from "./components/DeptChart";
import { KpiRow } from "./components/KpiRow";
import { PerformanceTable } from "./components/PerformanceTable";
import { TopBar } from "./components/TopBar";
import { TrendChart } from "./components/TrendChart";
import {
  fetchCatalog,
  fetchSnapshot,
  type Catalog,
  type DashboardFilters,
  type Snapshot,
} from "./lib/dashboard";

export default function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [filters, setFilters] = useState<DashboardFilters | null>(null);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await fetchCatalog();
        if (cancelled) return;
        setCatalog(c);
        setFilters({
          week: c.latest_week,
          department: "all",
          model: "all",
          sku: "all",
          channel: "all",
        });
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!filters) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const s = await fetchSnapshot(filters);
        if (cancelled) return;
        setSnap(s);
        setError(null);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [filters]);

  if (!catalog || !filters) {
    return (
      <div className="wrap" style={{ padding: 24 }}>
        <p className="mut">
          {error
            ? `Could not load catalog — is the API on :8001? (${error})`
            : "Loading catalog…"}
        </p>
      </div>
    );
  }

  return (
    <>
      <TopBar
        catalog={catalog}
        filters={filters}
        onChange={setFilters}
        onReset={() =>
          setFilters({
            week: catalog.latest_week,
            department: "all",
            model: "all",
            sku: "all",
            channel: "all",
          })
        }
      />
      <div className="wrap">
        <div className="left" style={{ opacity: loading ? 0.55 : 1 }}>
          {error && !snap && (
            <p className="mut" style={{ padding: 8 }}>
              {error}
            </p>
          )}
          {snap && (
            <>
              <KpiRow kpis={snap.kpis} />
              <div className="rowA">
                <TrendChart
                  title={`Net sales vs target — ${snap.scope_label}`}
                  sub={`${snap.channel_label} · S$'000 · trailing ${snap.trend.labels.length} weeks`}
                  labels={snap.trend.labels}
                  actual={snap.trend.actual}
                  plan={snap.trend.plan}
                  highlightIndex={snap.trend.highlight_index}
                />
                <DeptChart
                  weekLabel={snap.week}
                  labels={snap.dept_variance.labels}
                  values={snap.dept_variance.values}
                />
              </div>
              <div className="rowB">
                <PerformanceTable
                  filters={filters}
                  table={snap.table}
                  week={snap.week}
                  onChange={setFilters}
                />
                <ChanChart
                  labels={snap.channel_split.labels}
                  stores={snap.channel_split.stores}
                  ecom={snap.channel_split.ecom}
                />
              </div>
            </>
          )}
        </div>
        <ChatPanel />
      </div>
    </>
  );
}
