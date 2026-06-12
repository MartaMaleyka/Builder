/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#faf8f4",
        surface: "#f0ece5",
        border: "#e0d8ce",
        primary: "#1c1814",
        secondary: "#776e65",
        accent: "#7c6af7",
        success: "#2a8a5a",
        error: "#c94040",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "8px",
        sm: "4px",
        md: "6px",
        lg: "8px",
      },
    },
  },
  plugins: [],
};
