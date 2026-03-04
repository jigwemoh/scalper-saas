"use client";

import { useEffect, useState } from "react";
import { accountsApi, riskApi } from "@/lib/api";
import { Shield, AlertTriangle, CheckCircle } from "lucide-react";
import { clsx } from "clsx";

type PerfRow = {
  date: string;
  starting_balance: number;
  ending_balance: number;
  daily_return_percent: number;
  total_trades: number;
};

type RiskEvent = {
  id: string;
  event_type: string;
  description: string;
  triggered_at: string;
};

export default function RiskPage() {
  const [ks, setKs] = useState<{ blocked: boolean; level: string; reason: string } | null>(null);
  const [perf, setPerf] = useState<PerfRow[]>([]);
  const [events, setEvents] = useState<RiskEvent[]>([]);

  useEffect(() => {
    accountsApi.list().then((res) => {
      if (res.data.length > 0) {
        const id = res.data[0].id;
        riskApi.killSwitch(id).then((r) => setKs(r.data));
        riskApi.performance(id, 14).then((r) => setPerf(r.data));
        riskApi.events(id, 20).then((r) => setEvents(r.data));
      }
    });
  }, []);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Risk Management</h1>

      {/* Kill switch status */}
      <div
        className={clsx(
          "flex items-center gap-4 rounded-xl border p-5",
          ks?.blocked
            ? "bg-sell/10 border-sell/30"
            : "bg-buy/10 border-buy/30"
        )}
      >
        {ks?.blocked ? (
          <AlertTriangle className="w-6 h-6 text-sell shrink-0" />
        ) : (
          <CheckCircle className="w-6 h-6 text-buy shrink-0" />
        )}
        <div>
          <div className={clsx("font-semibold", ks?.blocked ? "text-sell" : "text-buy")}>
            {ks?.blocked ? "Trading Paused" : "Trading Active"}
          </div>
          <div className="text-sm text-muted mt-0.5">
            {ks?.reason || "All kill switch conditions within limits"}
          </div>
        </div>
        <div className="ml-auto text-xs bg-bg/50 border border-border px-3 py-1.5 rounded-lg text-muted">
          Level: {ks?.level || "none"}
        </div>
      </div>

      {/* Kill switch thresholds info */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Soft Pause", value: "-6% daily", color: "text-yellow-400" },
          { label: "Daily Kill", value: "-8% daily", color: "text-sell" },
          { label: "Weekly Kill", value: "-12% weekly", color: "text-sell" },
        ].map((t) => (
          <div key={t.label} className="bg-surface border border-border rounded-xl p-4">
            <div className={`text-lg font-bold ${t.color}`}>{t.value}</div>
            <div className="text-xs text-muted mt-1">{t.label}</div>
          </div>
        ))}
      </div>

      {/* Daily performance table */}
      {perf.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted mb-3">14-Day Performance</h2>
          <div className="bg-surface border border-border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted">
                  {["Date", "Starting Balance", "Ending Balance", "Daily Return", "Trades"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {perf.map((row) => (
                  <tr key={row.date} className="hover:bg-bg/50">
                    <td className="px-4 py-3 font-medium">{row.date}</td>
                    <td className="px-4 py-3">${row.starting_balance.toFixed(2)}</td>
                    <td className="px-4 py-3">${row.ending_balance.toFixed(2)}</td>
                    <td className={clsx(
                      "px-4 py-3 font-semibold",
                      row.daily_return_percent >= 0 ? "text-buy" : "text-sell"
                    )}>
                      {row.daily_return_percent >= 0 ? "+" : ""}{row.daily_return_percent.toFixed(2)}%
                    </td>
                    <td className="px-4 py-3 text-muted">{row.total_trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Risk events */}
      {events.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted mb-3">Risk Events Log</h2>
          <div className="space-y-2">
            {events.map((e) => (
              <div key={e.id} className="bg-surface border border-sell/20 rounded-lg px-4 py-3 flex items-start gap-3">
                <Shield className="w-4 h-4 text-sell mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-medium text-sell">{e.event_type}</div>
                  <div className="text-xs text-muted mt-0.5">{e.description}</div>
                </div>
                <div className="ml-auto text-xs text-muted">{new Date(e.triggered_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
