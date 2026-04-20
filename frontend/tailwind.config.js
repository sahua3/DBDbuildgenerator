/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Bebas Neue'", "cursive"],
        body: ["'DM Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        blood: {
          50: "#fef2f2",
          100: "#ffe1e1",
          200: "#ffc7c7",
          300: "#ffa0a0",
          400: "#ff6b6b",
          500: "#f83b3b",
          600: "#e51d1d",
          700: "#c11414",
          800: "#9f1414",
          900: "#841818",
          950: "#480707",
        },
        ash: {
          50: "#f6f6f7",
          100: "#e1e3e7",
          200: "#c3c7cf",
          300: "#9da3b0",
          400: "#787f92",
          500: "#5e6578",
          600: "#4b5063",
          700: "#3e4152",
          800: "#363945",
          900: "#30323c",
          950: "#1a1b22",
        },
        fog: {
          DEFAULT: "#8ba3b8",
          light: "#c4d4e0",
          dark: "#4a6275",
        },
      },
      backgroundImage: {
        "fog-gradient": "linear-gradient(135deg, #0d0f14 0%, #1a1d27 50%, #0d0f14 100%)",
        "blood-glow": "radial-gradient(ellipse at top, rgba(200,20,20,0.15) 0%, transparent 70%)",
      },
      animation: {
        "fade-up": "fadeUp 0.4s ease forwards",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        flicker: "flicker 4s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        flicker: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.85" },
          "75%": { opacity: "0.95" },
        },
      },
    },
  },
  plugins: [],
};
