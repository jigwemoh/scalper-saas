"use client";

import { useEffect, useState } from "react";
import { accountsApi, tradesApi } from "@/lib/api";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";

type Trade = {
  id: string;
  symbol: string;
  direction: string;
  lot_size: number;
  entry_price: number | null;
  exit_price: number | null;
  profit_loss: number | null;
  status: string;
  opened_at: string | null;
};

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    accountsApi.list().then((res) => {
      if (res.data.length > 0) {
        const id = res.data[0].id;
        tradesApi.history(id, 50).then((t) => {
          setTrades(t.data.trades);
          setLoading(false);
        });
      } else {
        setLoading(false);
      }
    });
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-xl font-semibold mb-4">Trade History</h1>
        <div className="text-muted text-sm">Loading trades...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Trade History</h1>

      {trades.length === 0 ? (
        <div className="bg-surface border border-border rounded-xl p-12 text-center text-muted">
          No trades yet. Connect your MT5 account to start receiving signals.
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-muted">
                {["Symbol", "Direction", "Lots", "Entry", "Exit", "P&L", "Status", "Opened"].map(
                  (h) => (
                    <th key={h} className="text-left px-4 py-3 font-medium">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {trades.map((trade) => {
                const isBuy = trade.direction === "BUY";
                const pnl = trade.profit_loss;
                return (
                  <tr key={trade.id} className="hover:bg-bg/50 transition-colors">
                    <td className="px-4 py-3 font-medium">{trade.symbol}</td>
                    <td className="px-4 py-3">
                      <span
                        className={clsx(
                          "px-2 py-0.5 rounded text-xs font-medium",
                          isBuy ? "bg-buy/10 text-buy" : "bg-sell/10 text-sell"
                        )}
                      >
                        {trade.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted">{trade.lot_size}</td>
                    <td className="px-4 py-3 font-mono">{trade.entry_price ?? "—"}</td>
                    <td className="px-4 py-3 font-mono">{trade.exit_price ?? "—"}</td>
                    <td className={clsx("px-4 py-3 font-semibold", pnl == null ? "text-muted" : pnl >= 0 ? "text-buy" : "text-sell")}>
                      {pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={clsx(
                          "px-2 py-0.5 rounded text-xs",
                          trade.status === "open" ? "bg-accent/10 text-accent" : "bg-border text-muted"
                        )}
                      >
                        {trade.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted text-xs">
                      {trade.opened_at
                        ? formatDistanceToNow(new Date(trade.opened_at), { addSuffix: true })
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
