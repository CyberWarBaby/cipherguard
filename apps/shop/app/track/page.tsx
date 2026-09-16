"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function TrackEntryPage() {
  const [value, setValue] = useState("");
  const router = useRouter();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (value.trim()) router.push(`/orders/${encodeURIComponent(value.trim())}`);
  }

  return (
    <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-md text-center">
        <h1 className="font-display text-3xl text-ink">Track your order</h1>
        <p className="mt-2 text-ink/60">
          Enter the order reference from your confirmation to see live status
          from ShipFast Logistics.
        </p>
        <form onSubmit={handleSubmit} className="mt-8 flex gap-2 text-left">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. ord_1758012345"
            className="input"
            autoFocus
          />
          <button
            type="submit"
            className="shrink-0 border border-indigo bg-indigo px-5 py-2.5 text-sm font-medium text-parchment hover:bg-indigo-deep"
          >
            Track
          </button>
        </form>
      </div>
    </div>
  );
}
