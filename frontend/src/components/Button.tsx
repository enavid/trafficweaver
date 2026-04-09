import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  children: ReactNode
}

const variantStyles: Record<string, React.CSSProperties> = {
  primary: {
    background: 'var(--color-primary)',
    color: 'var(--color-text-inverse)',
  },
  secondary: {
    background: 'var(--color-surface-offset)',
    color: 'var(--color-text)',
    border: '1px solid var(--color-border)',
  },
  danger: {
    background: 'var(--color-error)',
    color: '#fff',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--color-text-muted)',
  },
}

const sizeClasses: Record<string, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all',
        'hover:opacity-90 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none',
        sizeClasses[size],
        className,
      )}
      style={variantStyles[variant]}
      {...props}
    >
      {children}
    </button>
  )
}
