/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        kali: {
          bg: '#0a0c10',
          panel: '#0f1117',
          border: '#1f2937',
          vortex: '#3b82f6',
          reaper: '#ef4444',
          gravity: '#8b5cf6',
          divide: '#14b8a6',
          score: '#f59e0b',
        },
      },
    },
  },
  plugins: [],
};
