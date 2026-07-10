"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

type DailyCost = {
  day: string;
  total_spans: number;
  total_errors: number;
  total_cost_usd: number;
};

type Totals = {
  total_llm_calls: number;
  total_cost_usd: number;
  total_errors: number;
  total_agent_runs: number;
};

export default function Analytics() {
  const [daily, setDaily] = useState<DailyCost[]>([]);
  const [totals, setTotals] = useState<Totals | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8001/v1/analytics/cost")
      .then((res) => res.json())
      .then((data) => {
        setDaily(Array.isArray(data.daily) ? data.daily : []);
        setTotals(data.totals);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8">Loading analytics...</div>;

  // avoid crashing if there's no LLM span data yet
  const successRate = totals && totals.total_llm_calls > 0
    ? (((totals.total_llm_calls - totals.total_errors) / totals.total_llm_calls) * 100).toFixed(1)
    : "0.0";

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <Link href="/" className="text-blue-400 hover:underline text-sm">← back to traces</Link>
      <h1 className="text-2xl font-bold mt-4 mb-6">Cost & ROI Analytics</h1>

      {/* summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="border border-gray-700 rounded p-4">
          <div className="text-xs text-gray-400">Total LLM Calls</div>
          <div className="text-2xl font-bold">{totals?.total_llm_calls ?? 0}</div>
        </div>
        <div className="border border-gray-700 rounded p-4">
          <div className="text-xs text-gray-400">Total Cost</div>
          <div className="text-2xl font-bold">
            ${(totals?.total_cost_usd ?? 0).toFixed(4)}
          </div>
        </div>
        <div className="border border-gray-700 rounded p-4">
          <div className="text-xs text-gray-400">Success Rate</div>
          <div className="text-2xl font-bold text-green-400">{successRate}%</div>
        </div>
        <div className="border border-gray-700 rounded p-4">
          <div className="text-xs text-gray-400">Agent Runs</div>
          <div className="text-2xl font-bold">{totals?.total_agent_runs ?? 0}</div>
        </div>
      </div>

      {/* daily breakdown table */}
      <h2 className="text-lg font-semibold mb-3">Daily Breakdown</h2>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-left border-b border-gray-700">
            <th className="py-2 pr-4">Date</th>
            <th className="py-2 pr-4">LLM Calls</th>
            <th className="py-2 pr-4">Errors</th>
            <th className="py-2 pr-4">Cost</th>
          </tr>
        </thead>
        <tbody>
          {daily.map((d) => (
            <tr key={d.day} className="border-b border-gray-800">
              <td className="py-2 pr-4">{d.day}</td>
              <td className="py-2 pr-4">{d.total_spans}</td>
              <td className="py-2 pr-4">
                {d.total_errors > 0 ? (
                  <span className="text-red-500">{d.total_errors}</span>
                ) : (
                  <span className="text-green-500">0</span>
                )}
              </td>
              <td className="py-2 pr-4">${d.total_cost_usd?.toFixed(4) ?? "0.0000"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {daily.length === 0 && (
        <p className="text-gray-500">No LLM spans with cost data yet.</p>
      )}
    </main>
  );
}