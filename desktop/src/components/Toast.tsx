import { useEffect } from 'react'

interface Props {
  message: string
  type: 'success' | 'error'
  onDismiss: () => void
  durationMs?: number
}

export default function Toast({ message, type, onDismiss, durationMs = 2500 }: Props) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, durationMs)
    return () => clearTimeout(timer)
  }, [onDismiss, durationMs])

  return <div className={`toast toast-${type}`}>{message}</div>
}
