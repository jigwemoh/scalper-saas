import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ScalperAI — MT5 Signal Platform",
  description: "AI-driven scalping signals for MT5 traders",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg text-white min-h-screen antialiased">{children}</body>
    </html>
  );
}
