/** @type {import('tailwindcss').Config} */

// --- palette ---
// colours are CSS variables (rgb channels) defined in src/index.css
//   brand #00B4D8 (hover #48CAE4) · accent gold #D4AF37
//   hits: exact #34D399, diff #6FBF97, winner #94AD9F · miss #F87171 · live #EF4444 · warn #FBBF24
//   surface 900..500 = #0B0E14 #111827 #1E2536 #2A3347 #3B4763 · label = white tag behind logos
const v = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // brand = everything interactive, accent = rare "special" moments,
        // the rest only when it means something (hit / miss / live / warning)
        brand: {
          DEFAULT: v('brand'),       // buttons, links, active nav, focus, progress, selected chips
          light:   v('brand-light'), // hover on brand
          ink:     v('brand-ink'),   // text on a brand background
        },
        accent: {
          DEFAULT: v('accent'),      // gold — podium #1, joker, higher stake, badges
        },
        hit: {
          exact:  v('hit-exact'),    // strongest — dokładny wynik
          diff:   v('hit-diff'),     // softer — różnica bramek
          winner: v('hit-winner'),   // muted — tylko zwycięzca
        },
        miss: v('miss'),             // pudło
        live: v('live'),             // na żywo
        warn: v('warn'),             // ostrzeżenie, zamyka się wkrótce
        surface: {
          900: v('surface-900'),
          800: v('surface-800'),
          700: v('surface-700'),
          600: v('surface-600'),
          500: v('surface-500'),
        },
        // light label behind competition logos and team crests (dark logos stay visible)
        label: {
          DEFAULT: v('label'),
          ink:     v('label-ink'),
        },
        // text greys (tailwind defaults, as variables)
        gray: {
          50:  v('gray-50'),
          100: v('gray-100'),
          200: v('gray-200'),
          300: v('gray-300'),
          400: v('gray-400'),
          500: v('gray-500'),
          600: v('gray-600'),
          700: v('gray-700'),
          800: v('gray-800'),
          900: v('gray-900'),
        },
      },
      // small radii everywhere (no big rounded boxes), values in src/index.css
      borderRadius: {
        sm:      'var(--r-sm)',
        DEFAULT: 'var(--r)',
        md:      'var(--r-md)',
        lg:      'var(--r-lg)',
        xl:      'var(--r-xl)',
        '2xl':   'var(--r-2xl)',
        '3xl':   'var(--r-3xl)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        // wordmark only (czutka)
        display: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        // logo wordmark (teal → red)
        'gradient-logo': 'linear-gradient(90deg, #00B4D8 0%, #E61D25 100%)',
      },
      boxShadow: {
        'glow-brand':  '0 0 20px rgb(var(--c-brand) / 0.30)',
        'glow-live':   '0 0 20px rgb(var(--c-live) / 0.30)',
        'glow-accent': '0 0 20px rgb(var(--c-accent) / 0.35)',
        'card':        'var(--shadow-card)',
        'card-hover':  'var(--shadow-card-hover)',
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
