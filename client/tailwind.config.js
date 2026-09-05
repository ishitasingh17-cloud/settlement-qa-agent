/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        'surface-muted': 'var(--color-surface-muted)',
        'surface-elevated': 'var(--color-surface-elevated)',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
        'icon-primary': 'var(--color-icon-primary)',
        'icon-secondary': 'var(--color-icon-secondary)',
        'icon-muted': 'var(--color-icon-muted)',
        border: 'var(--color-border)',
        'border-subtle': 'var(--color-border-subtle)',
        primary: 'var(--color-primary)',
        'primary-dark': 'var(--color-primary-dark)',
        'ai-tint': 'var(--color-ai-tint)',
        'ai-border': 'var(--color-ai-border)',
        'status-success': '#16A34A',
        'status-warning': '#D97706',
        'status-danger': '#DC2626',
        'status-info': '#2563EB',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
};
