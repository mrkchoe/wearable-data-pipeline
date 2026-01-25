import { useEffect, useMemo, useState } from "react";
import { onLCP } from "web-vitals";
import { EventName } from "../types/events";
import { identify, setDevice, track } from "../lib/analytics/track";

const vendors = ["fitbit", "apple_health", "garmin", "oura", "whoop", "other"];
const metrics = ["steps", "sleep", "calories", "distance", "active_minutes"];
const ranges = ["day", "week", "month", "custom"];

function simulateDashboardFetch(): Promise<{ status: number }> {
  return new Promise((resolve) => {
    setTimeout(() => resolve({ status: 200 }), 220);
  });
}

export default function Dashboard() {
  const [vendor, setVendor] = useState<string>("fitbit");
  const [metric, setMetric] = useState<string>("steps");
  const [range, setRange] = useState<string>("week");
  const [goalTarget, setGoalTarget] = useState<number>(8000);

  const sessionId = useMemo(() => `session_${Date.now()}`, []);

  useEffect(() => {
    onLCP((metricEntry) => {
      track(EventName.PerfLcp, {
        lcp_ms: Math.round(metricEntry.value),
        page_type: "dashboard",
      });
    });
  }, []);

  useEffect(() => {
    const start = performance.now();
    simulateDashboardFetch()
      .then(() => {
        track(EventName.PerfApiLatency, {
          api_latency_ms: Math.round(performance.now() - start),
          endpoint: "/api/dashboard",
          status_code: 200,
        });
      })
      .catch((error: Error) => {
        track(EventName.ApiError, {
          endpoint: "/api/dashboard",
          status_code: 500,
          error_code: "DASHBOARD_FETCH_FAILED",
          error_message: error.message,
        });
      });
  }, []);

  const handleConnectDevice = () => {
    track(EventName.ConnectDeviceStarted, { vendor });
    try {
      track(EventName.ConnectDeviceSucceeded, {
        vendor,
        device_model: "Wearable Pro X",
      });
      setDevice("device-12345");
    } catch (error) {
      track(EventName.ConnectDeviceFailed, {
        vendor,
        error_code: "DEVICE_CONNECT_FAILED",
        error_message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  const handleSync = () => {
    track(EventName.SyncRequested, {
      vendor,
      date_range: range,
      sync_status: "requested",
    });

    try {
      track(EventName.SyncCompleted, {
        vendor,
        date_range: range,
        sync_status: "completed",
        records_synced: 42,
      });
    } catch (error) {
      track(EventName.SyncFailed, {
        vendor,
        date_range: range,
        sync_status: "failed",
        error_code: "SYNC_FAILED",
        error_message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  const handleMetricView = () => {
    track(EventName.MetricViewed, {
      metric_type: metric,
      date_range: range,
      vendor,
    });
  };

  const handleGoalCreate = () => {
    track(EventName.GoalCreated, {
      metric_type: metric,
      target_value: goalTarget,
      target_unit: metric === "sleep" ? "minutes" : "count",
      date_range: range,
    });
  };

  const handleExport = () => {
    track(EventName.ExportClicked, {
      export_format: "csv",
      date_range: range,
      vendor,
    });
  };

  const handleUiError = () => {
    track(EventName.UiError, {
      component: "GoalCard",
      error_code: "VALIDATION_FAILED",
      error_message: "Goal target must be positive",
      severity: "warning",
    });
  };

  const handleIdentify = () => {
    identify("user-123");
    track(EventName.Identify, {
      user_status: "known",
    });
  };

  return (
    <section style={{ borderTop: "1px solid #eee", paddingTop: 16 }}>
      <h2>Dashboard</h2>
      <p>
        Session: <strong>{sessionId}</strong>
      </p>
      <div style={{ display: "grid", gap: 12, maxWidth: 640 }}>
        <label>
          Vendor
          <select
            value={vendor}
            onChange={(event) => setVendor(event.target.value)}
            style={{ marginLeft: 8 }}
          >
            {vendors.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          Metric
          <select
            value={metric}
            onChange={(event) => setMetric(event.target.value)}
            style={{ marginLeft: 8 }}
          >
            {metrics.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          Date range
          <select
            value={range}
            onChange={(event) => setRange(event.target.value)}
            style={{ marginLeft: 8 }}
          >
            {ranges.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          Goal target
          <input
            type="number"
            value={goalTarget}
            onChange={(event) => setGoalTarget(Number(event.target.value))}
            style={{ marginLeft: 8 }}
          />
        </label>
      </div>

      <div style={{ marginTop: 16, display: "flex", flexWrap: "wrap", gap: 8 }}>
        <button onClick={handleIdentify}>Identify user</button>
        <button onClick={handleConnectDevice}>Connect device</button>
        <button onClick={handleSync}>Sync</button>
        <button onClick={handleMetricView}>View metric</button>
        <button onClick={handleGoalCreate}>Create goal</button>
        <button onClick={handleExport}>Export</button>
        <button onClick={handleUiError}>Trigger UI error</button>
      </div>
    </section>
  );
}
