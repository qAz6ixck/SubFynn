/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: '#23212C',
        surface: {
          card: 'rgba(28, 25, 36, 0.70)',
          'card-hover': 'rgba(38, 34, 50, 0.85)',
          header: 'rgba(43, 38, 56, 0.80)',
          input: 'rgba(22, 20, 29, 0.85)',
          dropdown: '#292436',
        },
        border: {
          glass: 'rgba(255, 255, 255, 0.08)',
          card: '#3D374D',
          input: '#433C55',
        },
        brand: {
          indigo: '#6366F1',
          'indigo-hover': '#4F46E5',
          cyan: '#38BDF8',
          'cyan-hover': '#0284C7',
          emerald: '#10B981',
          'emerald-bg': '#13382D',
          rose: '#F43F5E',
          'rose-hover': '#E11D48',
          violet: '#8B5CF6',
          pink: '#EC4899',
        },
        content: {
          white: '#FFFFFF',
          muted: '#A6A0B5',
          dim: '#7B758D',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Kanit', '-apple-system', 'Segoe UI', 'sans-serif'],
        thai: ['Kanit', 'Leelawadee UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
        glass: '16px',
      },
      boxShadow: {
        'glass-card': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glow-indigo': '0 0 25px -5px rgba(99, 102, 241, 0.4)',
        'glow-cyan': '0 0 25px -5px rgba(56, 189, 248, 0.4)',
        'glow-pink': '0 0 30px -5px rgba(236, 72, 153, 0.35)',
      },
    },
  },
  plugins: [],
};
