/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // FIFA World Cup 2026 official palette
        mundial: {
          teal: '#00B4D8',
          magenta: '#E6007E',
          orange: '#FF6B35',
          gold: '#FFD700',
          navy: '#0A1128',
        },
        // app surfaces — dark theme
        surface: {
          900: '#0B0E14',  // page background
          800: '#111827',  // card background
          700: '#1E2536',  // card hover / elevated
          600: '#2A3347',  // input background
          500: '#3B4763',  // borders
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-mundial': 'linear-gradient(135deg, #00B4D8 0%, #E6007E 50%, #FF6B35 100%)',
        'gradient-teal-magenta': 'linear-gradient(135deg, #00B4D8 0%, #E6007E 100%)',
        'gradient-card': 'linear-gradient(145deg, rgba(30,37,54,0.8) 0%, rgba(17,24,39,0.9) 100%)',
      },
      boxShadow: {
        'glow-teal': '0 0 20px rgba(0, 180, 216, 0.3)',
        'glow-magenta': '0 0 20px rgba(230, 0, 126, 0.3)',
        'glow-orange': '0 0 20px rgba(255, 107, 53, 0.3)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.3)',
        'card-hover': '0 8px 40px rgba(0, 0, 0, 0.5)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient-x': 'gradient-x 3s ease infinite',
        'slide-up': 'slide-up 0.3s ease-out',
        'fade-in': 'fade-in 0.4s ease-out',
      },
      keyframes: {
        'gradient-x': {
          '0%, 100%': { 'background-position': '0% 50%' },
          '50%': { 'background-position': '100% 50%' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
