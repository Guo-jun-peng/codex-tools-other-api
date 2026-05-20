interface Props {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  title?: string
}

export default function Toggle({ checked, onChange, disabled, title }: Props) {
  return (
    <button
      className={`toggle-switch ${checked ? 'toggle-on' : 'toggle-off'}`}
      onClick={() => onChange(!checked)}
      disabled={disabled}
      title={title}
    >
      <span className="toggle-knob" />
    </button>
  )
}
