/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        hardlock: {
          950: '#0a0e17',
          900: '#0f1520',
          800: '#1a2332',
          700: '#243044',
          600: '#2d3a52',
          500: '#3b82f6',
          400: '#60a5fa',
          accent: '#22d3ee',
          danger: '#ef4444',
          success: '#22c55e',
          warning: '#f59e0b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};
