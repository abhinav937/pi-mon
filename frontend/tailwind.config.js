/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  darkMode: 'class', // Use class-based dark mode to match App.js toggling
  theme: {
    extend: {
      screens: {
        'xs': '475px',
        '3xl': '1600px',
        '4xl': '1920px',
      },
      colors: {
        // Custom color palette
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        },
        success: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'Noto Sans', 'sans-serif'],
        mono: ['Fira Code', 'ui-monospace', 'SFMono-Regular', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
        // Mobile-specific spacing
        '11': '2.75rem',
        '13': '3.25rem',
        '15': '3.75rem',
        '17': '4.25rem',
        '19': '4.75rem',
        '21': '5.25rem',
        '23': '5.75rem',
        '25': '6.25rem',
        '27': '6.75rem',
        '29': '7.25rem',
        '31': '7.75rem',
        '33': '8.25rem',
        '35': '8.75rem',
        '37': '9.25rem',
        '39': '9.75rem',
        '41': '10.25rem',
        '43': '10.75rem',
        '45': '11.25rem',
        '47': '11.75rem',
        '49': '12.25rem',
        '51': '12.75rem',
        '53': '13.25rem',
        '55': '13.75rem',
        '57': '14.25rem',
        '59': '14.75rem',
        '61': '15.25rem',
        '63': '15.75rem',
        '65': '16.25rem',
        '67': '16.75rem',
        '69': '17.25rem',
        '71': '17.75rem',
        '73': '18.25rem',
        '75': '18.75rem',
        '77': '19.25rem',
        '79': '19.75rem',
        '81': '20.25rem',
        '83': '20.75rem',
        '85': '21.25rem',
        '87': '21.75rem',
        '89': '22.25rem',
        '91': '22.75rem',
        '93': '23.25rem',
        '95': '23.75rem',
        '97': '24.25rem',
        '99': '24.75rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'fade-out': 'fadeOut 0.5s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'slide-out': 'slideOut 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
        'spin-slow': 'spin 3s linear infinite',
        // Mobile-specific animations
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'scale-out': 'scaleOut 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        slideOut: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-100%)' },
        },
        // Mobile-specific keyframes
        slideUp: {
          '0%': { transform: 'translateY(100%)' },
          '100%': { transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(100%)' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)' },
          '100%': { transform: 'scale(1)' },
        },
        scaleOut: {
          '0%': { transform: 'scale(1)' },
          '100%': { transform: 'scale(0.95)' },
        },
      },
      boxShadow: {
        'soft': '0 2px 15px 0 rgba(0, 0, 0, 0.05)',
        'medium': '0 4px 20px 0 rgba(0, 0, 0, 0.1)',
        'hard': '0 8px 30px 0 rgba(0, 0, 0, 0.15)',
        // Mobile-specific shadows
        'mobile': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'mobile-lg': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'mobile-xl': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
      },
      backdropBlur: {
        'xs': '2px',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        // Mobile-specific border radius
        'mobile': '0.75rem',
        'mobile-lg': '1rem',
        'mobile-xl': '1.25rem',
      },
      maxWidth: {
        '8xl': '88rem',
        '9xl': '96rem',
        // Mobile-specific max widths
        'mobile': '100vw',
        'mobile-sm': '95vw',
        'mobile-md': '90vw',
        'mobile-lg': '85vw',
      },
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
        // Mobile-specific z-index
        'mobile-menu': '1000',
        'mobile-overlay': '999',
        'mobile-modal': '1001',
      },
      // Mobile-specific sizing
      minHeight: {
        'mobile-button': '44px',
        'mobile-input': '44px',
        'mobile-touch': '48px',
      },
      minWidth: {
        'mobile-button': '44px',
        'mobile-input': '44px',
        'mobile-touch': '48px',
      },
      // Mobile-specific typography
      fontSize: {
        'mobile-xs': ['0.75rem', { lineHeight: '1rem' }],
        'mobile-sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'mobile-base': ['1rem', { lineHeight: '1.5rem' }],
        'mobile-lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'mobile-xl': ['1.25rem', { lineHeight: '1.75rem' }],
        'mobile-2xl': ['1.5rem', { lineHeight: '2rem' }],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms')({
      strategy: 'class',
    }),
    // Custom plugin for component utilities
    function({ addComponents, theme }) {
      addComponents({
        '.btn': {
          padding: theme('spacing.2') + ' ' + theme('spacing.4'),
          borderRadius: theme('borderRadius.md'),
          fontWeight: theme('fontWeight.medium'),
          fontSize: theme('fontSize.sm'),
          lineHeight: theme('lineHeight.5'),
          transition: 'all 0.2s ease-in-out',
          '&:focus': {
            outline: 'none',
            boxShadow: theme('boxShadow.md'),
          },
          '&:disabled': {
            opacity: theme('opacity.50'),
            cursor: 'not-allowed',
          },
        },
        '.card': {
          backgroundColor: theme('colors.white'),
          borderRadius: theme('borderRadius.lg'),
          boxShadow: theme('boxShadow.sm'),
          border: '1px solid ' + theme('colors.gray.200'),
          padding: theme('spacing.6'),
          '@media (prefers-color-scheme: dark)': {
            backgroundColor: theme('colors.gray.800'),
            borderColor: theme('colors.gray.700'),
          }
        },
        '.metric-card': {
          backgroundColor: theme('colors.white'),
          borderRadius: theme('borderRadius.lg'),
          boxShadow: theme('boxShadow.sm'),
          border: '1px solid ' + theme('colors.gray.200'),
          padding: theme('spacing.6'),
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            boxShadow: theme('boxShadow.md'),
          },
          '@media (prefers-color-scheme: dark)': {
            backgroundColor: theme('colors.gray.800'),
            borderColor: theme('colors.gray.700'),
          }
        },
        // Mobile-specific components
        '.mobile-card': {
          backgroundColor: theme('colors.white'),
          borderRadius: theme('borderRadius.mobile'),
          boxShadow: theme('boxShadow.mobile'),
          border: '1px solid ' + theme('colors.gray.200'),
          padding: theme('spacing.4'),
          transition: 'all 0.2s ease-in-out',
          '@media (prefers-color-scheme: dark)': {
            backgroundColor: theme('colors.gray.800'),
            borderColor: theme('colors.gray.700'),
          }
        },
        '.mobile-button': {
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: theme('spacing.2'),
          padding: theme('spacing.3'),
          borderRadius: theme('borderRadius.lg'),
          transition: 'all 0.2s ease-in-out',
          minHeight: theme('minHeight.mobile-touch'),
          fontSize: theme('fontSize.sm'),
          fontWeight: theme('fontWeight.medium'),
        },
        '.mobile-input': {
          display: 'block',
          width: '100%',
          padding: theme('spacing.3') + ' ' + theme('spacing.2'),
          border: '1px solid ' + theme('colors.gray.300'),
          borderRadius: theme('borderRadius.md'),
          boxShadow: theme('boxShadow.sm'),
          fontSize: '16px', // Prevent zoom on iOS
          minHeight: theme('minHeight.mobile-input'),
          '&:focus': {
            outline: 'none',
            ring: '2px',
            ringColor: theme('colors.blue.500'),
            borderColor: theme('colors.blue.500'),
          },
          '@media (prefers-color-scheme: dark)': {
            backgroundColor: theme('colors.gray.700'),
            borderColor: theme('colors.gray.600'),
            color: theme('colors.white'),
            '&:focus': {
              ringColor: theme('colors.blue.400'),
              borderColor: theme('colors.blue.400'),
            },
          }
        },
      })
    }
  ],
}
