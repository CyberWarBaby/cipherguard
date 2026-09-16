"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Category } from "@/lib/types";
import { productsByCategory } from "@/lib/catalog";
import ProductCard from "@/components/ProductCard";
import CategoryRail from "@/components/CategoryRail";

export default function HomePage() {
  const [category, setCategory] = useState<Category | "all">("all");
  const products = useMemo(() => productsByCategory(category), [category]);

  return (
    <div className="mx-auto max-w-content px-4 sm:px-6">
      {/* Hero */}
      <section className="grid gap-10 py-12 sm:py-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div>
          <p className="text-sm font-medium text-clay">Market day, every day</p>
          <h1 className="mt-3 max-w-md font-display text-4xl leading-[1.1] text-ink sm:text-5xl">
            Everything for today&rsquo;s list, from sellers who know their craft.
          </h1>
          <p className="mt-5 max-w-sm text-ink/65">
            Fabric cut to size, spice ground fresh, gadgets that actually ship —
            ordered in minutes, tracked door to door.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-4">
            <a
              href="#stalls"
              className="border border-ochre-deep bg-ochre px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-ochre-deep"
            >
              Start shopping
            </a>
            <Link
              href="/track"
              className="text-sm font-medium text-indigo-deep underline decoration-indigo/30 underline-offset-4 hover:decoration-indigo-deep"
            >
              Track an existing order
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-3 grid-rows-2 gap-2 sm:gap-3">
          <HeroTile className="col-span-2 row-span-1" tone="clay" label="Fashion & Fabric" pattern="dots" />
          <HeroTile className="col-span-1 row-span-2" tone="indigo" label="Electronics" pattern="stitch" />
          <HeroTile className="col-span-1 row-span-1" tone="leaf" label="Food & Spice" pattern="diamond" />
          <HeroTile className="col-span-1 row-span-1" tone="ochre" label="Beauty" pattern="dots" />
        </div>
      </section>

      {/* Category rail + grid */}
      <section id="stalls" className="scroll-mt-24 py-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <h2 className="font-display text-2xl text-ink">Browse the stalls</h2>
          <p className="hidden text-sm text-ink/50 sm:block">
            {products.length} item{products.length === 1 ? "" : "s"}
          </p>
        </div>
        <CategoryRail active={category} onSelect={setCategory} />
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      </section>
    </div>
  );
}

const TONE: Record<string, { bg: string; fg: string }> = {
  clay: { bg: "#F6E1D7", fg: "#A23E1B" },
  indigo: { bg: "#E4E9F0", fg: "#223A5E" },
  leaf: { bg: "#E7EEE3", fg: "#3F6B3F" },
  ochre: { bg: "#FBEDD8", fg: "#B4741C" },
};

function HeroTile({
  className = "",
  tone,
  label,
  pattern,
}: {
  className?: string;
  tone: keyof typeof TONE;
  label: string;
  pattern: "dots" | "stitch" | "diamond";
}) {
  const c = TONE[tone];
  const patId = `hero-${tone}-${pattern}`;
  return (
    <div className={`relative overflow-hidden border border-ink/10 ${className}`}>
      <svg viewBox="0 0 120 120" className="h-full w-full" preserveAspectRatio="xMidYMid slice">
        <rect width="120" height="120" fill={c.bg} />
        <defs>
          <pattern id={patId} width="20" height="20" patternUnits="userSpaceOnUse">
            {pattern === "dots" && <circle cx="4" cy="4" r="2.2" fill={c.fg} opacity="0.5" />}
            {pattern === "stitch" && (
              <rect x="0" y="8" width="20" height="3" fill={c.fg} opacity="0.4" />
            )}
            {pattern === "diamond" && (
              <path d="M10 0 L20 10 L10 20 L0 10 Z" fill="none" stroke={c.fg} strokeWidth="1.2" opacity="0.5" />
            )}
          </pattern>
        </defs>
        <rect width="120" height="120" fill={`url(#${patId})`} />
      </svg>
      <span
        className="absolute bottom-2 left-2 bg-white/85 px-2 py-1 text-[11px] font-medium"
        style={{ color: c.fg }}
      >
        {label}
      </span>
    </div>
  );
}
