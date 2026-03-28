/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        xhs: {
          red: '#FF2442',
          dark: '#1A1A1A',
        }
      }
    },
  },
  plugins: [],
}
