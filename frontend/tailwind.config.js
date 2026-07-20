/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: '#C0392B',      /* 深酒红 */
          'primary-light': '#E74C3C', /* 亮红 */
          'bg-warm': '#FDF2F0',    /* 米白 */
        },
      },
    },
  },
  plugins: [],
}
