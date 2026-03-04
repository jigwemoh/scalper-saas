"use client";

import { useEffect, useState } from "react";
import { authApi, accountsApi, subscriptionApi } from "@/lib/api";
import { Copy, Key, Plus } from "lucide-react";

type ApiKey = { id: string; key: string; name: string | null };

export default function SettingsPage() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [subscription, setSubscription] = useState<{ status: string; plan: string | null } | null>(null);
  const [newKeyName, setNewKeyName] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const [plans, setPlans] = useState<{ name: string; price_usd_monthly: number }[]>([]);

  useEffect(() => {
    subscriptionApi.mine().then((r) => setSubscription(r.data));
    subscriptionApi.plans().then((r) => setPlans(r.data));
    // Load API keys from user session (they come with register/login)
    // In production, add GET /auth/api-keys endpoint
  }, []);

  async function createKey() {
    const res = await authApi.createApiKey(newKeyName || undefined);
    setApiKeys([...apiKeys, res.data]);
    setNewKeyName("");
  }

  function copyKey(key: string) {
    navigator.clipboard.writeText(key);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="p-6 space-y-8 max-w-2xl">
      <h1 className="text-xl font-semibold">Settings</h1>

      {/* Subscription */}
      <section className="bg-surface border border-border rounded-xl p-5 space-y-4">
        <h2 className="font-medium">Subscription</h2>
        <div className="flex items-center gap-3">
          <div
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              subscription?.status === "active"
                ? "bg-buy/10 text-buy"
                : "bg-sell/10 text-sell"
            }`}
          >
            {subscription?.status || "Loading..."}
          </div>
          {subscription?.plan && (
            <span className="text-sm text-muted capitalize">{subscription.plan} plan</span>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3 mt-2">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className="border border-border rounded-lg p-3 text-center space-y-1 hover:border-accent cursor-pointer transition-colors"
            >
              <div className="text-sm font-semibold capitalize">{plan.name}</div>
              <div className="text-xl font-bold">${plan.price_usd_monthly}</div>
              <div className="text-xs text-muted">/month</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted">
          Payments via Paystack. Contact support to upgrade your plan.
        </p>
      </section>

      {/* API Keys */}
      <section className="bg-surface border border-border rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Key className="w-4 h-4 text-accent" />
          <h2 className="font-medium">API Keys</h2>
        </div>
        <p className="text-xs text-muted">
          Use your API key in the MT5 Expert Advisor to receive signals automatically.
        </p>

        {/* Create new key */}
        <div className="flex gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. MT5 EA)"
            className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
          />
          <button
            onClick={createKey}
            className="flex items-center gap-2 bg-accent hover:bg-accent/80 text-white px-4 py-2 rounded-lg text-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create
          </button>
        </div>

        {/* Key list */}
        {apiKeys.length > 0 && (
          <div className="space-y-2">
            {apiKeys.map((k) => (
              <div
                key={k.id}
                className="flex items-center gap-3 bg-bg border border-border rounded-lg px-4 py-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-muted">{k.name || "Unnamed key"}</div>
                  <div className="font-mono text-xs truncate mt-0.5">{k.key}</div>
                </div>
                <button
                  onClick={() => copyKey(k.key)}
                  className="text-muted hover:text-white transition-colors"
                >
                  <Copy className="w-4 h-4" />
                </button>
                {copied === k.key && (
                  <span className="text-xs text-buy">Copied!</span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
