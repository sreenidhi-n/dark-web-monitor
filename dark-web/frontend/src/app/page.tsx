"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { getFindings, getSources, getWatchlists, getAlertHistory } from "@/lib/api";

const CHART_PLACEHOLDER = Array.from({ length: 7 }, (_, i) => ({
  day: `Day ${i + 1}`,
  findings: Math.floor(Math.random() * 40 + 5),
}));

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-5">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-3xl font-semibold text-gray-100">{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const { data: findings } = useQuery({ queryKey: ["findings"], queryFn: () => getFindings() });
  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });
  const { data: watchlists } = useQuery({ queryKey: ["watchlists"], queryFn: getWatchlists });
  const { data: alerts } = useQuery({ queryKey: ["alerts"], queryFn: getAlertHistory });

  const todayAlerts =
    alerts?.filter(
      (a) => new Date(a.triggered_at).toDateString() === new Date().toDateString()
    ).length ?? 0;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <h1 className="text-xl font-semibold text-gray-100">Overview</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Findings" value={findings?.total ?? "—"} />
        <StatCard label="Active Sources" value={sources?.filter((s) => s.is_active).length ?? "—"} />
        <StatCard label="Watchlists" value={watchlists?.filter((w) => w.is_active).length ?? "—"} />
        <StatCard label="Alerts Today" value={todayAlerts} />
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-5">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-4">Findings — Last 7 Days</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={CHART_PLACEHOLDER}>
            <XAxis dataKey="day" stroke="#4b5563" tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <YAxis stroke="#4b5563" tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 6 }}
              labelStyle={{ color: "#e5e7eb" }}
            />
            <Bar dataKey="findings" fill="#ef4444" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
