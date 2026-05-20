import type { ReactNode } from 'react'

interface Props {
  title: string
  children: ReactNode
  onClose: () => void
  variant?: 'default' | 'danger'
  footer?: ReactNode
}

export default function Modal({ title, children, onClose, variant = 'default', footer }: Props) {
  const titleColor = variant === 'danger' ? 'var(--danger)' : undefined
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className={`modal${variant === 'danger' ? ' modal-confirm' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="card-title" style={titleColor ? { color: titleColor } : undefined}>
          {title}
        </h3>
        {children}
        {footer && <div className="btn-group" style={{ marginTop: 16 }}>{footer}</div>}
      </div>
    </div>
  )
}
