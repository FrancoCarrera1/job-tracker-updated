/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0c0d0f",
        ash: "#1a1c20",
      },
    },
  },
  plugins: [],
};
