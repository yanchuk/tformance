module.exports = {
  darkMode: ["class", '[data-theme="dark"]'],
  // Note: Tailwind v4 ignores 'content' and 'safelist' options (uses automatic detection)
  // Safelist classes are defined via @source inline() in site-tailwind.css
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Base background colors - Easy Eyes inspired warm neutrals
        deep: '#1e1e1e',      // Softer main background
        surface: '#282725',   // Warm cards, panels
        elevated: '#363636',  // Subtler borders, dividers
        muted: '#9a9690',     // Warm muted text

        // New accent system - warm coral/orange palette
        accent: {
          primary: '#F97316',   // Coral orange - main brand, CTAs
          secondary: '#FDA4AF', // Warm rose - highlights
          tertiary: '#2DD4BF',  // Teal - success, positive metrics
          warning: '#FBBF24',   // Amber - caution states
          info: '#60A5FA',      // Soft blue - informational
          error: '#F87171',     // Soft red - errors, negative metrics
        },

        // Legacy cyan - keep for backwards compatibility during migration
        cyan: {
          DEFAULT: '#5e9eb0',  // Muted teal - softer than #06b6d4
          light: '#7ab5c4',    // Light muted teal
          dark: '#4a8a9c',     // Dark muted teal
        },
        'cyan-bright': '#06b6d4',
      },
      aspectRatio: {
        '3/2': '3 / 2',
      },
      animation: {
        'typewriter': 'typewriter 2s steps(40) forwards',
        'blink': 'blink 1s step-end infinite',
        'fade-up': 'fadeUp 0.6s ease-out forwards',
        'fade-up-delay-1': 'fadeUp 0.6s ease-out 0.1s forwards',
        'fade-up-delay-2': 'fadeUp 0.6s ease-out 0.2s forwards',
        'fade-up-delay-3': 'fadeUp 0.6s ease-out 0.3s forwards',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
      },
      keyframes: {
        typewriter: {
          'from': { width: '0' },
          'to': { width: '100%' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        fadeUp: {
          'from': { opacity: '0', transform: 'translateY(20px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
    container: {
      center: true,
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
