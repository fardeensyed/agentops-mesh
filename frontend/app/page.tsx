"use client";
import { useEffect, useState } from "react";

// shape of one trace row coming back from /v1/traces
type Trace = {
  trace_id: string;
  root_name: string;
  started_at: string;
  ended_at: string;
  span_count: number;
  error_count: number;
};

export default function Dashboard() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // fetch directly from your FastAPI gateway
    fetch("http://localhost:8001/v1/traces")
      .then((res) => res.json())
      .then((data) => {
        setTraces(data.traces);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8">Loading traces...</div>;

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">AgentOps Mesh — Traces</h1>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-left border-b border-gray-700">
            <th className="py-2 pr-4">Agent</th>
            <th className="py-2 pr-4">Spans</th>
            <th className="py-2 pr-4">Errors</th>
            <th className="py-2 pr-4">Started</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr key={t.trace_id} className="border-b border-gray-800">
              <td className="py-2 pr-4 font-mono">{t.root_name}</td>
              <td className="py-2 pr-4">{t.span_count}</td>
              <td className="py-2 pr-4">
                {t.error_count > 0 ? (
                  <span className="text-red-500">{t.error_count}</span>
                ) : (
                  <span className="text-green-500">0</span>
                )}
              </td>
              <td className="py-2 pr-4 text-gray-400">
                {new Date(t.started_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {traces.length === 0 && (
        <p className="text-gray-500">No traces yet — run your SDK tests.</p>
      )}
    </main>
  );
}