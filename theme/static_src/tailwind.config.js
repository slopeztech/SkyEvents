/** @type {import('tailwindcss').Config} */
module.exports = {
  // Scan all templates and Python files for class names.
  // Paths are relative to this file (theme/static_src/).
  content: [
    "../../sky_events/templates/**/*.html",
    "../../sky_events/apps/**/*.py",
    "../../sky_events/apps/**/*.html",
    "../../config/**/*.py",
  ],

  // Dark mode via class on <html> element — toggled by JS
  darkMode: "class",

  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },

  plugins: [],

  // Classes used dynamically (e.g. hero-bg-{{ style }}) must be safelisted
  // so Tailwind does not purge them during the content scan.
  safelist: [
    { pattern: /^hero-bg-/ },
    { pattern: /^timeline-dot-/ },
    { pattern: /^badge-/ },
  ],
};
