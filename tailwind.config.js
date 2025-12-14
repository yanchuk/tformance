module.exports = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [],
  safelist: [
    'alert-success',
    'alert-info',
    'alert-error',
    'alert-warning',
    'pg-bg-danger',
    'pg-bg-success',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Base background colors (dark slate)
        deep: '#0f172a',      // Slate 900 - deepest background
        surface: '#1e293b',   // Slate 800 - card backgrounds
        elevated: '#334155',  // Slate 700 - elevated elements
        muted: '#94a3b8',     // Slate 400 - muted text (lighter for better contrast)
        // Primary accent - softer teal (was harsh cyan)
        cyan: {
          DEFAULT: '#5e9eb0',  // Muted teal - softer than #06b6d4
          light: '#7ab5c4',    // Light muted teal
          dark: '#4a8a9c',     // Dark muted teal
        },
        // Keep reference to old cyan for migration
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
