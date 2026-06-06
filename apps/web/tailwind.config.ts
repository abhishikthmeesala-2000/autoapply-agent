import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        glow: "0 0 0 1px rgba(148, 163, 184, 0.16), 0 24px 80px rgba(15, 23, 42, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
