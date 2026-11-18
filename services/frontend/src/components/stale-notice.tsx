// The "old forecast" warning. Amber on a pale amber tint, with words: colour is never the only
// signal. `compact` is the short form used inside a plan row.
export function StaleNotice({ compact = false }: { compact?: boolean }) {
  return (
    <p className="rounded-md bg-stale-tint px-3 py-2 text-sm text-stale">
      <span aria-hidden="true">⚠ </span>
      <strong className="font-bold">Old forecast</strong>
      {compact ? null : (
        <>
          <br />
          The weather service could not refresh, so these numbers use the last forecast it had.
        </>
      )}
    </p>
  );
}
