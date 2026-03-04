"use client";

import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, AlertTriangle, Activity } from "lucide-react";
import { useWebSocket } from "@/lib/websocket";
import { useAppStore } from "@/lib/store";
import { riskApi, accountsApi } from "@/lib/api";
import EquityCurve from "@/components/charts/EquityCurve";

export default function DashboardPage() {
  const { accountInfo, setAccountInfo, killSwitchActive, setKillSwitch, signals } = useAppStore();
  const [accounts, setAccounts] = useState<{ id: string }[]>([]);
  const [performance, setPerformance] = useState<{
    date: string; daily_return_percent: number
  }[]>([]);

  useWebSocket((msg) => {
    if (msg.type === "account_update") {
      setAccountInfo(msg.data as Parameters<typeof setAccountInfo>[0]);
    }
    if (msg.type === "kill_switch") {
      const d = msg.data as { triggered: boolean; reason: string };
      setKillSwitch(d.triggered, d.reason);
    }
  });

  useEffect(() => {
    accountsApi.list().then((res) => {
      setAccounts(res.data);
      if (res.data.length > 0) {
        const id = res.data[0].id;
        riskApi.killSwitch(id).then((ks) =>
          setKillSwitch(ks.data.blocked, ks.data.reason)
        );
        riskApi.performance(id, 14).then((p) =>
          setPerformance(p.data.reverse())
        );
      }
    });
  }, []);

  const todayReturn = performance[performance.length - 1]?.daily_return_percent ?? 0;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Overview</h1>

      {/* Kill switch banner */}
      {killSwitchActive && (
        <div className="flex items-center gap-3 bg-sell/10 border border-sell/30 text-sell rounded-lg px-4 py-3 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>Trading paused: kill switch active. New signals will not be dispatched.</span>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Equity"
          value={accountInfo ? `$${accountInfo.equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "—"}
          icon={<TrendingUp className="w-4 h-4" />}
          color="accent"
        />
        <StatCard
          label="Balance"
          value={accountInfo ? `$${accountInfo.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "—"}
          icon={<TrendingUp className="w-4 h-4" />}
          color="buy"
        />
        <StatCard
          label="Today P&L"
          value={`${todayReturn >= 0 ? "+" : ""}${todayReturn.toFixed(2)}%`}
          icon={todayReturn >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          color={todayReturn >= 0 ? "buy" : "sell"}
        />
        <StatCard
          label="Active Signals (1h)"
          value={String(signals.length)}
          icon={<Activity className="w-4 h-4" />}
          color="accent"
        />
      </div>

      {/* Equity curve */}
      {performance.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-muted mb-4">14-Day Equity Curve</h2>
          <EquityCurve data={performance} />
        </div>
      )}
    </div>
  );
}

function StatCard({
  label, value, icon, color,
}: {
  label: string; value: string; icon: React.ReactNode; color: "accent" | "buy" | "sell";
}) {
  const colorMap = {
    accent: "text-accent bg-accent/10",
    buy: "text-buy bg-buy/10",
    sell: "text-sell bg-sell/10",
  };
  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colorMap[color]}`}>
        {icon}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}
