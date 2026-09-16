import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        parchment: "#F6F1E4",
        parchment2: "#EFE7D3",
        ink: "#1C1B18",
        indigo: {
          DEFAULT: "#223A5E",
          deep: "#16283F",
          light: "#3C5C89",
          tint: "#E4E9F0",
        },
        ochre: {
          DEFAULT: "#D98F2B",
          deep: "#B4741C",
          tint: "#FBEDD8",
        },
        clay: {
          DEFAULT: "#A23E1B",
          tint: "#F6E1D7",
        },
        leaf: {
          DEFAULT: "#3F6B3F",
          tint: "#E7EEE3",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "3px",
      },
      maxWidth: {
        content: "1240px",
      },
    },
  },
  plugins: [],
};
export default config;
