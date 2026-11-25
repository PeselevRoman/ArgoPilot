// A small chevron drawn as an icon. It marks "this goes somewhere" at the end of a row, and it is
// hidden from screen readers (the link's words already say it).
export function Chevron({ direction = "right", className = "" }: { direction?: "left" | "right"; className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={`size-5 shrink-0 ${className}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={direction === "right" ? "M9 5l7 7-7 7" : "M15 5l-7 7 7 7"} />
    </svg>
  );
}
