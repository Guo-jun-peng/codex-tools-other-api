import type { ReactNode } from 'react'

type BadgeVariant = 'success' | 'danger' | 'warning'

interface Props {
  variant: BadgeVariant
  children: ReactNode
  style?: React.CSSProperties
}

export default function Badge({ variant, children, style }: Props) {
  return (
    <span className={`badge badge-${variant}`} style={style}>
      {children}
    </span>
  )
}
