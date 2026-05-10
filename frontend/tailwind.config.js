/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        md: {
          primary: "#002395",
          "on-primary": "#FFFFFF",
          container: "#DDE4FF",
          "on-container": "#001945",
          secondary: "#D35F00",
          surface: "#FEFBFF",
          "surface-container": "#F0F2FA",
          outline: "#757780",
          error: "#BA1A1A",
        },
      },
      borderRadius: {
        md: "8px",
      },
      boxShadow: {
        md1: "0 1px 2px rgba(2, 6, 23, .10), 0 8px 24px rgba(0, 35, 149, .08)",
        md2: "0 2px 6px rgba(2, 6, 23, .12), 0 16px 36px rgba(0, 35, 149, .10)",
      },
    },
  },
  plugins: [],
};
