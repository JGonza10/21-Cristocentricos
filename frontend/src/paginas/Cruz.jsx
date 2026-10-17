export default function Cruz({ tam = 22 }) {
  return (
    <span className="cruz" aria-hidden="true">
      <svg width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke="var(--on-wine)" strokeWidth="2.6" strokeLinecap="round">
        <path d="M12 3v18M6 9h12" />
      </svg>
    </span>
  )
}
