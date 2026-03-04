"use client";

import { useEffect, useState } from "react";
import { accountsApi } from "@/lib/api";
import { Link2, ServerCog } from "lucide-react";

type Account = {
  id: string;
  broker_name: string | null;
  account_number: string | null;
  server_name: string | null;
  leverage: number | null;
  account_balance: number | null;
  account_equity: number | null;
  risk_profile: string;
  is_active: boolean;
};

export default function AccountPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [form, setForm] = useState({
    broker_name: "",
    account_number: "",
    server_name: "",
    leverage: 100,
    risk_profile: "balanced",
  });
  const [linking, setLinking] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    accountsApi.list().then((r) => setAccounts(r.data));
  }, []);

  async function handleLink(e: React.FormEvent) {
    e.preventDefault();
    setLinking(true);
    try {
      await accountsApi.link(form);
      const updated = await accountsApi.list();
      setAccounts(updated.data);
      setSuccess(true);
    } finally {
      setLinking(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-xl font-semibold">MT5 Account</h1>

      {/* Existing accounts */}
      {accounts.map((acc) => (
        <div key={acc.id} className="bg-surface border border-border rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <ServerCog className="w-4 h-4 text-accent" />
            <span className="font-medium">{acc.broker_name || "Unknown broker"}</span>
            <span
              className={`ml-auto px-2 py-0.5 rounded-full text-xs ${
                acc.is_active ? "bg-buy/10 text-buy" : "bg-sell/10 text-sell"
              }`}
            >
              {acc.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              { label: "Account #", value: acc.account_number },
              { label: "Server", value: acc.server_name },
              { label: "Leverage", value: acc.leverage ? `1:${acc.leverage}` : "—" },
              { label: "Risk Profile", value: acc.risk_profile },
              { label: "Balance", value: acc.account_balance ? `$${acc.account_balance.toFixed(2)}` : "—" },
              { label: "Equity", value: acc.account_equity ? `$${acc.account_equity.toFixed(2)}` : "—" },
            ].map((f) => (
              <div key={f.label}>
                <div className="text-xs text-muted">{f.label}</div>
                <div className="mt-0.5">{f.value || "—"}</div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Link new account */}
      <div className="bg-surface border border-border rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Link2 className="w-4 h-4 text-accent" />
          <h2 className="font-medium">Link MT5 Account</h2>
        </div>

        {success && (
          <div className="bg-buy/10 border border-buy/30 text-buy text-sm rounded-lg px-4 py-2.5">
            Account linked successfully. The performance tracker will sync your balance shortly.
          </div>
        )}

        <form onSubmit={handleLink} className="space-y-3">
          {[
            { label: "Broker Name", key: "broker_name", placeholder: "e.g. IC Markets" },
            { label: "Account Number", key: "account_number", placeholder: "e.g. 12345678" },
            { label: "MT5 Server", key: "server_name", placeholder: "e.g. ICMarketsSC-Demo" },
          ].map((f) => (
            <div key={f.key}>
              <label className="block text-xs text-muted mb-1">{f.label}</label>
              <input
                type="text"
                value={(form as Record<string, string | number>)[f.key] as string}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                placeholder={f.placeholder}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
              />
            </div>
          ))}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-muted mb-1">Leverage</label>
              <select
                value={form.leverage}
                onChange={(e) => setForm({ ...form, leverage: Number(e.target.value) })}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
              >
                {[50, 100, 200, 500].map((l) => (
                  <option key={l} value={l}>1:{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">Risk Profile</label>
              <select
                value={form.risk_profile}
                onChange={(e) => setForm({ ...form, risk_profile: e.target.value })}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
              >
                <option value="conservative">Conservative</option>
                <option value="balanced">Balanced</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={linking}
            className="w-full bg-accent hover:bg-accent/80 disabled:opacity-50 text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
          >
            {linking ? "Linking..." : "Link Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
