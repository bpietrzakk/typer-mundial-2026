/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary accent — teal/cyan (oryginalne, rozpoznawalne)
        // Red — oficjalny kolor FIFA 2026 (akcent)
        // Gold — trofeum
        mundial: {
          teal:  '#00B4D8',  // primary — wszystkie active states, linki, akcenty
          red:   '#E61D25',  // accent — FIFA 2026 official red, live, ważne CTA
          gold:  '#C8A428',  // ranking, trofeum
          navy:  '#0A1128',  // ciemne tło
        },
        surface: {
          900: '#0B0E14',
          800: '#111827',
          700: '#1E2536',
          600: '#2A3347',
          500: '#3B4763',
        },
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        // Teal → Red — znajomy kolor + oficjalny akcent FIFA
        'gradient-mundial':   'linear-gradient(90deg, #00B4D8 0%, #E61D25 100%)',
        'gradient-teal-red':  'linear-gradient(135deg, #00B4D8 0%, #E61D25 100%)',
        'gradient-card':      'linear-gradient(145deg, rgba(30,37,54,0.8) 0%, rgba(17,24,39,0.9) 100%)',
      },
      boxShadow: {
        'glow-teal': '0 0 20px rgba(0, 180, 216, 0.35)',
        'glow-red':  '0 0 20px rgba(230, 29, 37, 0.35)',
        'glow-gold': '0 0 20px rgba(200, 164, 40, 0.35)',
        'card':      '0 4px 24px rgba(0, 0, 0, 0.3)',
        'card-hover':'0 8px 40px rgba(0, 0, 0, 0.5)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient-x': 'gradient-x 3s ease infinite',
        'slide-up':   'slide-up 0.3s ease-out',
        'fade-in':    'fade-in 0.4s ease-out',
      },
      keyframes: {
        'gradient-x': {
          '0%, 100%': { 'background-position': '0% 50%' },
          '50%':       { 'background-position': '100% 50%' },
        },
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
