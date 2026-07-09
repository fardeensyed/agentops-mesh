"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

type Span = {
  span_id: string;
  parent_span_id: string | null;
  name: string;
  span_kind: string;
  status: string;
  error_message: string | null;
  start_time: string;
  duration_ms: number;
  attributes: string; // JSON string
};

export default function TraceDetail() {
  const params = useParams();
  const traceId = params.trace_id as string;
  const [spans, setSpans] = useState<Span[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8001/v1/traces/${traceId}`)
      .then((res) => res.json())
      .then((data) => {
        setSpans(data.spans);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [traceId]);

  if (loading) return <div className="p-8">Loading spans...</div>;

  return (
    <main className="p-8 max-w-4xl mx-auto">
      <Link href="/" className="text-blue-400 hover:underline text-sm">← back to traces</Link>
      <h1 className="text-xl font-bold mt-4 mb-6 font-mono">{traceId}</h1>

      <div className="space-y-2">
        {spans.map((s) => {
          // indent child spans slightly, based on whether they have a parent
          const isChild = s.parent_span_id !== null;
          const attrs = JSON.parse(s.attributes || "{}");

          return (
            <div
              key={s.span_id}
              className={`border rounded p-3 ${isChild ? "ml-8 border-gray-700" : "border-gray-600"} ${
                s.status === "error" ? "bg-red-950/30 border-red-800" : ""
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="font-mono font-semibold">{s.name}</span>
                <span className="text-xs text-gray-400">{s.duration_ms?.toFixed(2)}ms</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                kind: {s.span_kind} · status:{" "}
                <span className={s.status === "error" ? "text-red-400" : "text-green-400"}>
                  {s.status}
                </span>
              </div>
              {s.error_message && (
                <div className="text-xs text-red-400 mt-1">{s.error_message}</div>
              )}
              {Object.keys(attrs).length > 0 && (
                <div className="text-xs text-gray-400 mt-2 font-mono">
                  {JSON.stringify(attrs)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </main>
  );
}