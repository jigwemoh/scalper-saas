import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0f1117",
        surface: "#1a1d27",
        border: "#2d3148",
        accent: "#6c63ff",
        buy: "#00d97e",
        sell: "#ff4757",
        muted: "#8892a4",
      },
    },
  },
  plugins: [],
};

export default config;
