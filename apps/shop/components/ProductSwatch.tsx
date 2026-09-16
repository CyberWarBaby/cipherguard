import { Category, Product } from "@/lib/types";

const THEME: Record<Category, { bg: string; fg: string }> = {
  fashion: { bg: "#F6E1D7", fg: "#A23E1B" },
  food: { bg: "#E7EEE3", fg: "#3F6B3F" },
  electronics: { bg: "#E4E9F0", fg: "#223A5E" },
  beauty: { bg: "#FBEDD8", fg: "#B4741C" },
  home: { bg: "#E4E9F0", fg: "#16283F" },
  kids: { bg: "#FBEDD8", fg: "#D98F2B" },
};

// Deterministic small integer from a product id, used only to pick a
// pattern variant so the grid feels hand-picked rather than uniform.
function seedFrom(id: string): number {
  let sum = 0;
  for (let i = 0; i < id.length; i++) sum += id.charCodeAt(i);
  return sum;
}

/**
 * A stand-in for a product photo: a small woven / shipfast-inspired geometric
 * pattern tinted per category, instead of a generic grey placeholder box.
 */
export default function ProductSwatch({ product }: { product: Product }) {
  const theme = THEME[product.category];
  const variant = seedFrom(product.id) % 3;
  const patternId = `pat-${product.id}`;

  return (
    <svg
      viewBox="0 0 200 160"
      className="h-full w-full"
      role="img"
      aria-label={`${product.name} pattern swatch`}
    >
      <rect width="200" height="160" fill={theme.bg} />
      <defs>
        <pattern
          id={patternId}
          width={variant === 0 ? 28 : variant === 1 ? 24 : 32}
          height={variant === 0 ? 28 : variant === 1 ? 24 : 32}
          patternUnits="userSpaceOnUse"
          patternTransform={variant === 1 ? "rotate(45)" : undefined}
        >
          {variant === 0 && (
            <>
              <circle cx="14" cy="14" r="3.2" fill={theme.fg} opacity="0.55" />
              <circle cx="0" cy="0" r="3.2" fill={theme.fg} opacity="0.35" />
              <circle cx="28" cy="0" r="3.2" fill={theme.fg} opacity="0.35" />
              <circle cx="0" cy="28" r="3.2" fill={theme.fg} opacity="0.35" />
              <circle cx="28" cy="28" r="3.2" fill={theme.fg} opacity="0.35" />
            </>
          )}
          {variant === 1 && (
            <>
              <rect x="0" y="10" width="24" height="4" fill={theme.fg} opacity="0.45" />
              <rect x="0" y="10" width="24" height="4" fill={theme.fg} opacity="0" />
            </>
          )}
          {variant === 2 && (
            <path
              d="M16 0 L32 16 L16 32 L0 16 Z"
              fill="none"
              stroke={theme.fg}
              strokeWidth="1.4"
              opacity="0.5"
            />
          )}
        </pattern>
      </defs>
      <rect width="200" height="160" fill={`url(#${patternId})`} />
      <rect
        x="0.75"
        y="0.75"
        width="198.5"
        height="158.5"
        fill="none"
        stroke={theme.fg}
        strokeOpacity="0.25"
        strokeWidth="1.5"
      />
    </svg>
  );
}
