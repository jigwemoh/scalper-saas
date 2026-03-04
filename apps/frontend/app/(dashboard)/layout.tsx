"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Activity, List, Shield, Settings, LogOut, TrendingUp } from "lucide-react";
import { clsx } from "clsx";

const NAV = [
  { href: "/dashboard", icon: BarChart2, label: "Overview" },
  { href: "/dashboard/signals", icon: Activity, label: "Signals" },
  { href: "/dashboard/trades", icon: List, label: "Trades" },
  { href: "/dashboard/risk", icon: Shield, label: "Risk" },
  { href: "/dashboard/settings", icon: Settings, label: "Settings" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  function handleLogout() {
    localStorage.clear();
    window.location.href = "/login";
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-surface border-r border-border flex flex-col shrink-0">
        <div className="p-4 border-b border-border flex items-center gap-2">
          <TrendingUp className="text-accent w-5 h-5" />
          <span className="font-bold text-sm">ScalperAI</span>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(({ href, icon: Icon, label }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                pathname === href
                  ? "bg-accent/20 text-accent"
                  : "text-muted hover:bg-bg hover:text-white"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          ))}
        </nav>

        <div className="p-3 border-t border-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted hover:text-sell hover:bg-sell/10 w-full transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-bg">
        {children}
      </main>
    </div>
  );
}
