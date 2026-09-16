"use client";

import { Category } from "@/lib/types";
import { CATEGORIES } from "@/lib/catalog";

interface Props {
  active: Category | "all";
  onSelect: (c: Category | "all") => void;
}

export default function CategoryRail({ active, onSelect }: Props) {
  return (
    <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
      <button
        onClick={() => onSelect("all")}
        className={`shrink-0 border px-4 py-2 text-sm transition-colors ${
          active === "all"
            ? "border-indigo bg-indigo text-parchment"
            : "border-ink/15 bg-white text-ink/70 hover:border-indigo/50"
        }`}
      >
        All stalls
      </button>
      {CATEGORIES.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id)}
          className={`shrink-0 border px-4 py-2 text-sm transition-colors ${
            active === c.id
              ? "border-indigo bg-indigo text-parchment"
              : "border-ink/15 bg-white text-ink/70 hover:border-indigo/50"
          }`}
        >
          {c.label}
        </button>
      ))}
    </div>
  );
}
