/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7fb",
          100: "#e9ecf4",
          200: "#cdd3e4",
          300: "#a4adc8",
          400: "#7c87ab",
          500: "#5d6791",
          600: "#465077",
          700: "#363e5f",
          800: "#262c47",
          900: "#161a2c",
          950: "#0b0d18",
        },
        brand: {
          500: "#6366f1",
          600: "#4f46e5",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Inter",
          "Roboto",
          "system-ui",
          "sans-serif",
        ],
        display: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      boxShadow: {
        glow: "0 0 0 4px rgba(99, 102, 241, 0.25)",
      },
    },
  },
  plugins: [],
};
