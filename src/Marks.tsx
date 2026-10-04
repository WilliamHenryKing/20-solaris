export function Arrow({ back = false, down = false }: { back?: boolean; down?: boolean }) {
  return (
    <svg
      className={`arrow-icon${back ? " arrow-back" : ""}${down ? " arrow-down" : ""}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M5 19 19 5M5 5h14v14" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export function SunMark() {
  return (
    <svg
      className="solar-mark"
      viewBox="0 0 160 160"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="80" cy="80" r="35" stroke="currentColor" strokeWidth="2" />
      <path
        d="M80 3v38M80 119v38M3 80h38M119 80h38M25.5 25.5l27 27M107.5 107.5l27 27M25.5 134.5l27-27M107.5 52.5l27-27"
        stroke="currentColor"
        strokeWidth="2"
      />
      <circle cx="80" cy="80" r="7" fill="currentColor" />
    </svg>
  );
}
