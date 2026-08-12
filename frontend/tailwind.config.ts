import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        "surface-2": "rgb(var(--color-surface-2) / <alpha-value>)",
        panel: "rgb(var(--color-surface) / 0.8)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        "line-bright": "rgb(var(--color-line-bright) / <alpha-value>)",
        primary: "#3b82f6",
        secondary: "#8b5cf6",
        accent: "#06b6d4",
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
        "text-primary": "rgb(var(--color-text-primary) / <alpha-value>)",
        "text-secondary": "rgb(var(--color-text-secondary) / <alpha-value>)",
        "text-muted": "rgb(var(--color-text-muted) / <alpha-value>)",
        electric: "#38BDF8",
        pulse: "#8B5CF6",
        mint: "#34D399",
        ember: "#F59E0B",
      },
      boxShadow: {
        glow: "0 0 28px rgba(59,130,246,0.28)",
        violet: "0 0 28px rgba(139,92,246,0.24)",
        panel: "0 24px 80px rgba(0,0,0,.35)",
        halo: "0 0 54px rgba(6,182,212,0.22)",
        "depth-1": "0 4px 16px rgba(0,0,0,0.18)",
        "depth-2": "0 12px 32px rgba(0,0,0,0.28)",
        "depth-3": "0 24px 64px rgba(0,0,0,0.38)",
        "depth-float": "0 30px 80px -12px rgba(59,130,246,0.25)",
      },
      borderRadius: {
        control: "var(--radius-control)",
        panel: "var(--radius-panel)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      keyframes: {
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 rgba(59,130,246,0)" },
          "50%": { boxShadow: "0 0 24px rgba(59,130,246,.32)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(320%)" },
        },
      },
      animation: {
        "fade-in-up": "fadeInUp .4s ease-out both",
        "scale-in": "scaleIn .2s ease-out both",
        "slide-in-right": "slideInRight .25s ease-out both",
        float: "float 5s ease-in-out infinite",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        scan: "scan 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
