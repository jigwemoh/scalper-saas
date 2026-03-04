import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl text-center space-y-6">
        <div className="inline-block px-3 py-1 rounded-full bg-accent/20 text-accent text-sm font-medium">
          AI-Powered · M1/M5 Scalping · MT5
        </div>

        <h1 className="text-5xl font-bold bg-gradient-to-r from-white to-accent bg-clip-text text-transparent">
          ScalperAI
        </h1>

        <p className="text-lg text-muted">
          Institutional-grade AI scalping signals delivered directly to your MT5 terminal.
          Rule-based filters + LSTM + XGBoost ensemble with strict risk management.
        </p>

        <div className="grid grid-cols-3 gap-4 py-4">
          {[
            { label: "Win Rate Target", value: "60–65%" },
            { label: "Risk per Trade", value: "0.5–2.5%" },
            { label: "Pairs", value: "EURUSD, GBPUSD, XAUUSD" },
          ].map((stat) => (
            <div key={stat.label} className="bg-surface border border-border rounded-lg p-4">
              <div className="text-xl font-bold text-accent">{stat.value}</div>
              <div className="text-sm text-muted mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="flex gap-4 justify-center">
          <Link
            href="/register"
            className="px-6 py-3 bg-accent hover:bg-accent/80 text-white rounded-lg font-medium transition-colors"
          >
            Get Started Free
          </Link>
          <Link
            href="/login"
            className="px-6 py-3 border border-border hover:border-accent text-white rounded-lg font-medium transition-colors"
          >
            Sign In
          </Link>
        </div>
      </div>
    </main>
  );
}
