import { Signal } from "@/lib/store";
import { clsx } from "clsx";
import { TrendingUp, TrendingDown, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function SignalCard({ signal }: { signal: Signal }) {
  const isBuy = signal.direction === "BUY";
  const confidence = Math.round(signal.probability * 100);
  const ago = formatDistanceToNow(new Date(signal.created_at), { addSuffix: true });

  return (
    <div className="bg-surface border border-border rounded-xl p-4 flex items-center gap-4">
      {/* Direction badge */}
      <div
        className={clsx(
          "w-12 h-12 rounded-xl flex items-center justify-center shrink-0",
          isBuy ? "bg-buy/10 text-buy" : "bg-sell/10 text-sell"
        )}
      >
        {isBuy ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
      </div>

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold">{signal.symbol}</span>
          <span
            className={clsx(
              "text-xs px-2 py-0.5 rounded-full font-medium",
              isBuy ? "bg-buy/10 text-buy" : "bg-sell/10 text-sell"
            )}
          >
            {signal.direction}
          </span>
          <span className="text-xs bg-surface border border-border rounded-full px-2 py-0.5 text-muted">
            {signal.timeframe}
          </span>
          {signal.regime && (
            <span className="text-xs text-muted">{signal.regime}</span>
          )}
        </div>

        <div className="flex items-center gap-4 mt-1 text-sm text-muted flex-wrap">
          {signal.entry_price && (
            <span>Entry: <span className="text-white">{signal.entry_price}</span></span>
          )}
          {signal.stop_loss && (
            <span>SL: <span className="text-sell">{signal.stop_loss}</span></span>
          )}
          {signal.take_profit && (
            <span>TP: <span className="text-buy">{signal.take_profit}</span></span>
          )}
        </div>
      </div>

      {/* Confidence + time */}
      <div className="text-right shrink-0">
        <div
          className={clsx(
            "text-lg font-bold",
            confidence >= 75 ? "text-buy" : confidence >= 68 ? "text-accent" : "text-muted"
          )}
        >
          {confidence}%
        </div>
        <div className="text-xs text-muted flex items-center gap-1 justify-end mt-0.5">
          <Clock className="w-3 h-3" />
          {ago}
        </div>
      </div>
    </div>
  );
}
