"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCart } from "@/lib/cart-context";

const LINKS = [
  { href: "/", label: "Shop" },
  { href: "/track", label: "Track order" },
  { href: "/account", label: "Account" },
];

export default function Navbar() {
  const { totalItems } = useCart();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-ink/10 bg-parchment/95 backdrop-blur">
      <div className="mx-auto flex max-w-content items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-display text-2xl tracking-tight text-indigo-deep">
            ShipFast
          </span>
          <span className="font-display text-2xl italic text-clay">Market</span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-ink/70 sm:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`transition-colors hover:text-indigo-deep ${
                pathname === link.href ? "text-indigo-deep font-medium" : ""
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/track"
            className="text-sm text-ink/70 hover:text-indigo-deep sm:hidden"
            aria-label="Track order"
          >
            Track
          </Link>
          <Link
            href="/cart"
            className="relative flex items-center gap-2 border border-ink/15 bg-white px-3 py-2 text-sm text-ink hover:border-indigo/50"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M3 4h2l2.4 12.2a2 2 0 0 0 2 1.6h7.2a2 2 0 0 0 2-1.6L21 8H6" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="9.5" cy="20.5" r="1.3" />
              <circle cx="17.5" cy="20.5" r="1.3" />
            </svg>
            <span className="hidden sm:inline">Cart</span>
            {totalItems > 0 && (
              <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-ochre text-[11px] font-semibold text-white">
                {totalItems}
              </span>
            )}
          </Link>
        </div>
      </div>
    </header>
  );
}
