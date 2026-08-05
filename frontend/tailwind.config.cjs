/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f7f4",
          100: "#dceee6",
          200: "#b7d9c8",
          500: "#2d6a4f",
          700: "#1b4332",
          800: "#123026",
          900: "#081c15",
          950: "#04100c",
        },
        surface: {
          50: "#f7faf8",
          100: "#eef4f0",
          200: "#d9e5de",
          300: "#b7c9bf",
          400: "#879e92",
          500: "#5f776b",
          600: "#455a50",
          700: "#33453d",
          800: "#22312b",
          900: "#15201c",
          950: "#0b1411",
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Fraunces"', "Georgia", "serif"],
      },
      fontSize: {
        xs: ["0.8125rem", { lineHeight: "1.25rem" }],
        sm: ["0.9375rem", { lineHeight: "1.45rem" }],
        base: ["1.0625rem", { lineHeight: "1.65rem" }],
        lg: ["1.1875rem", { lineHeight: "1.75rem" }],
        xl: ["1.3125rem", { lineHeight: "1.85rem" }],
        "2xl": ["1.5625rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
        "4xl": ["2.25rem", { lineHeight: "2.6rem" }],
      },
      boxShadow: {
        panel: "0 10px 30px -18px rgba(8, 28, 21, 0.35)",
      },
    },
  },
  plugins: [],
};
