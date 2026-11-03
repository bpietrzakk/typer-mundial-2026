/** @type {import('tailwindcss').Config} */

// --- palette ---
// colours are CSS variables (rgb channels) defined in src/index.css, so the
// whole look can be switched with one attribute on <html>:
//   default            = "Zieleń boiska" (trial, lighter pitch green, lines instead of cards)
//   data-theme=classic = the previous turquoise / navy look with rounded cards
// switch for a quick look: add ?theme=classic (or ?theme=pitch) to any url,
// it is remembered in localStorage (see the small script in index.html)
//
// pitch (default)                         classic (previous, for rollback)
//   brand        #3ECF6E  hover #5FE08A      brand        #00B4D8  hover #48CAE4
//   brand.ink    #06130B  text on brand      brand.ink    #0B0E14
//   accent       #D4AF37  gold               accent       #D4AF37
//   hit.exact    #5CE1E6  aqua               hit.exact    #34D399
//   hit.diff     #7EC3CF                     hit.diff     #6FBF97
//   hit.winner   #9EB6BD                     hit.winner   #94AD9F
//   miss #F87171 · live #EF4444 · warn #FBBF24 (both themes)
//   surface 900  #10241A  page               surface 900  #0B0E14
//   surface 800  #173123  raised             surface 800  #111827
//   surface 700  #1F3B2B                     surface 700  #1E2536
//   surface 600  #294A37                     surface 600  #2A3347
//   surface 500  #3A5E4A  lines (with /alpha) surface 500 #3B4763
//   gray 100     #E8F3EC  text               gray = tailwind default greys
//   gray 400     #8FA898  muted
// hits are aqua on purpose, so a "trafienie" never looks like a green button
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
        // text greys, slightly green tinted in the pitch theme
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
      // small radii everywhere in the pitch theme (no big rounded boxes),
      // classic theme puts the tailwind defaults back
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
        // classic theme wordmark (teal → red), unused in the pitch theme
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
