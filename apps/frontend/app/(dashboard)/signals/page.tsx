"use client";

import { useEffect } from "react";
import { signalsApi } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { useWebSocket } from "@/lib/websocket";
import SignalCard from "@/components/signals/SignalCard";

export default function SignalsPage() {
  const { signals, addSignal } = useAppStore();

  useWebSocket((msg) => {
    if (msg.type === "signal") {
      addSignal(msg.data as Parameters<typeof addSignal>[0]);
    }
  });

  useEffect(() => {
    signalsApi.recent(60).then((res) => {
      const loaded = res.data as Parameters<typeof addSignal>[0][];
      loaded.forEach((s) => addSignal(s));
    });
  }, []);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Live Signals</h1>
        <span className="text-xs text-muted bg-surface border border-border px-3 py-1 rounded-full">
          {signals.length} signals (last 60 min)
        </span>
      </div>

      {signals.length === 0 ? (
        <div className="bg-surface border border-border rounded-xl p-12 text-center text-muted">
          No signals yet. The AI engine scans every 60 seconds.
        </div>
      ) : (
        <div className="grid gap-3">
          {signals.map((signal) => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      )}
    </div>
  );
}
