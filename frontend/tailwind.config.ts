import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

export default {
  darkMode: ["class"],
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--ui-border) / <alpha-value>)",
        input: "hsl(var(--ui-input) / <alpha-value>)",
        ring: "hsl(var(--ui-ring) / <alpha-value>)",
        background: "hsl(var(--ui-background) / <alpha-value>)",
        foreground: "hsl(var(--ui-foreground) / <alpha-value>)",
        primary: {
          DEFAULT: "hsl(var(--ui-primary) / <alpha-value>)",
          foreground: "hsl(var(--ui-primary-foreground) / <alpha-value>)"
        },
        secondary: {
          DEFAULT: "hsl(var(--ui-secondary) / <alpha-value>)",
          foreground: "hsl(var(--ui-secondary-foreground) / <alpha-value>)"
        },
        destructive: {
          DEFAULT: "hsl(var(--ui-destructive) / <alpha-value>)",
          foreground: "hsl(var(--ui-destructive-foreground) / <alpha-value>)"
        },
        muted: {
          DEFAULT: "hsl(var(--ui-muted) / <alpha-value>)",
          foreground: "hsl(var(--ui-muted-foreground) / <alpha-value>)"
        },
        accent: {
          DEFAULT: "hsl(var(--ui-accent) / <alpha-value>)",
          foreground: "hsl(var(--ui-accent-foreground) / <alpha-value>)"
        },
        popover: {
          DEFAULT: "hsl(var(--ui-popover) / <alpha-value>)",
          foreground: "hsl(var(--ui-popover-foreground) / <alpha-value>)"
        },
        card: {
          DEFAULT: "hsl(var(--ui-card) / <alpha-value>)",
          foreground: "hsl(var(--ui-card-foreground) / <alpha-value>)"
        }
      },
      borderRadius: {
        lg: "var(--ui-radius)",
        md: "calc(var(--ui-radius) - 2px)",
        sm: "calc(var(--ui-radius) - 4px)",
        // Chat/answer surface radius scale — collapses the prior sprawl of
        // bespoke radii to three steps (pill = rounded-full).
        card: "1.25rem", // surface containers
        control: "0.75rem", // buttons, inputs, nested boxes
        chip: "0.5rem" // small tight elements
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" }
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" }
        }
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out"
      }
    },
  },
  plugins: [animate],
} satisfies Config;
