export default function Stars({ rating }: { rating: number }) {
  const full = Math.round(rating);
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <svg
          key={i}
          viewBox="0 0 20 20"
          className="h-3.5 w-3.5"
          fill={i < full ? "#D98F2B" : "none"}
          stroke="#D98F2B"
          strokeWidth="1"
        >
          <path d="M10 1.5l2.6 5.27 5.82.85-4.21 4.1 1 5.79L10 14.9l-5.21 2.6 1-5.78-4.2-4.1 5.8-.85L10 1.5z" />
        </svg>
      ))}
    </span>
  );
}
