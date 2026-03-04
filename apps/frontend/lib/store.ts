import { create } from "zustand";

export type Signal = {
  id: string;
  symbol: string;
  timeframe: string;
  direction: "BUY" | "SELL";
  probability: number;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  regime: string | null;
  session: string | null;
  created_at: string;
};

export type AccountInfo = {
  equity: number;
  balance: number;
  margin_used: number;
  margin_free: number;
  margin_level: number;
  leverage: number;
};

type AppStore = {
  signals: Signal[];
  accountInfo: AccountInfo | null;
  killSwitchActive: boolean;
  killSwitchReason: string;

  addSignal: (signal: Signal) => void;
  setAccountInfo: (info: AccountInfo) => void;
  setKillSwitch: (active: boolean, reason?: string) => void;
};

export const useAppStore = create<AppStore>((set) => ({
  signals: [],
  accountInfo: null,
  killSwitchActive: false,
  killSwitchReason: "",

  addSignal: (signal) =>
    set((state) => ({
      signals: [signal, ...state.signals].slice(0, 100), // Keep last 100
    })),

  setAccountInfo: (info) => set({ accountInfo: info }),

  setKillSwitch: (active, reason = "") =>
    set({ killSwitchActive: active, killSwitchReason: reason }),
}));
