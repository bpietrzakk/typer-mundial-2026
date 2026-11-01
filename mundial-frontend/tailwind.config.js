/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // one palette: brand = everything interactive, accent = rare "special" moments,
        // the rest only when it means something (hit / miss / live / warning)
        brand: {
          DEFAULT: '#00B4D8',  // buttons, links, active nav, focus, progress, selected chips
          light:   '#48CAE4',  // hover on brand
        },
        accent: {
          DEFAULT: '#D4AF37',  // gold — podium #1, joker, higher stake, badges
        },
        hit: {
          exact:  '#34D399',   // strongest green — dokładny wynik
          diff:   '#6FBF97',   // softer green — różnica bramek
          winner: '#94AD9F',   // muted green — tylko zwycięzca
        },
        miss: '#F87171',       // pudło
        live: '#EF4444',       // na żywo
        warn: '#FBBF24',       // ostrzeżenie, zamyka się wkrótce
        surface: {
          900: '#0B0E14',
          800: '#111827',
          700: '#1E2536',
          600: '#2A3347',
          500: '#3B4763',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        // logo wordmark only (czutka) — keep as is
        'gradient-logo': 'linear-gradient(90deg, #00B4D8 0%, #E61D25 100%)',
        'gradient-card': 'linear-gradient(145deg, rgba(30,37,54,0.8) 0%, rgba(17,24,39,0.9) 100%)',
      },
      boxShadow: {
        'glow-brand': '0 0 20px rgba(0, 180, 216, 0.35)',
        'glow-live':  '0 0 20px rgba(239, 68, 68, 0.3)',
        'glow-accent': '0 0 20px rgba(212, 175, 55, 0.35)',
        'card':       '0 4px 24px rgba(0, 0, 0, 0.3)',
        'card-hover': '0 8px 40px rgba(0, 0, 0, 0.5)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-up':   'slide-up 0.3s ease-out',
        'fade-in':    'fade-in 0.4s ease-out',
      },
      keyframes: {
        'slide-up': {
          '0%':   { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
