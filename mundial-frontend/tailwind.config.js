/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Official FIFA World Cup 2026 colors
        // Red = Canada, Green = Mexico, Blue = USA
        mundial: {
          red:    '#E61D25',  // Torch Red — official Canada color
          green:  '#3CAC3B',  // Average Green — official Mexico color
          blue:   '#2A398D',  // Hermes Blue — official USA color
          gold:   '#C8A428',  // Trophy gold
          navy:   '#0A1128',  // Deep dark background
        },
        // app surfaces — dark theme
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
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        // Official 2026 tri-color gradient: Kanada → Meksyk → USA
        'gradient-mundial': 'linear-gradient(90deg, #E61D25 0%, #3CAC3B 50%, #2A398D 100%)',
        // Two-color variants
        'gradient-red-green':  'linear-gradient(135deg, #E61D25 0%, #3CAC3B 100%)',
        'gradient-green-blue': 'linear-gradient(135deg, #3CAC3B 0%, #2A398D 100%)',
        'gradient-red-blue':   'linear-gradient(135deg, #E61D25 0%, #2A398D 100%)',
        'gradient-card': 'linear-gradient(145deg, rgba(30,37,54,0.8) 0%, rgba(17,24,39,0.9) 100%)',
      },
      boxShadow: {
        'glow-red':   '0 0 20px rgba(230, 29, 37, 0.35)',
        'glow-green': '0 0 20px rgba(60, 172, 59, 0.35)',
        'glow-blue':  '0 0 20px rgba(42, 57, 141, 0.35)',
        'card':       '0 4px 24px rgba(0, 0, 0, 0.3)',
        'card-hover': '0 8px 40px rgba(0, 0, 0, 0.5)',
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
