"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { shipfast, ShipFastOrder, ShipFastError } from "@/lib/shipfast";
import { getOrderHistory } from "@/lib/orders-store";
import { formatNaira, formatDate } from "@/lib/format";

const STATUS_STEPS = ["processing", "shipped", "delivered"];

export default function OrderTrackingPage({
  params,
}: {
  params: { id: string };
}) {
  const router = useRouter();
  const [order, setOrder] = useState<ShipFastOrder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lookup, setLookup] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    shipfast
      .getOrder(params.id)
      .then((o) => {
        if (!cancelled) setOrder(o);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ShipFastError) {
          setError(err.message);
        } else {
          setError("We couldn't reach ShipFast to look up this order.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  const localRecord = useMemo(
    () => getOrderHistory().find((o) => o.shipfastOrderId === params.id),
    [params.id]
  );

  const activeStepIndex = order
    ? Math.max(0, STATUS_STEPS.indexOf(order.status.toLowerCase()))
    : 0;

  function handleLookup(e: FormEvent) {
    e.preventDefault();
    if (lookup.trim()) router.push(`/orders/${encodeURIComponent(lookup.trim())}`);
  }

  return (
    <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
      <h1 className="font-display text-3xl text-ink">Track your order</h1>
      <p className="mt-1 text-sm text-ink/55">Order reference: {params.id}</p>

      {loading && (
        <div className="mt-8 border border-ink/10 bg-white p-10 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-indigo/30 border-t-indigo" />
          <p className="mt-4 text-ink/60">Checking with ShipFast…</p>
        </div>
      )}

      {!loading && error && (
        <div className="mt-8 border border-clay/30 bg-clay-tint p-6">
          <p className="font-display text-lg text-clay">We couldn&rsquo;t find that order</p>
          <p className="mt-2 text-sm text-ink/70">{error}</p>
        </div>
      )}

      {!loading && order && (
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_300px]">
          <div className="border border-ink/10 bg-white p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-display text-xl text-ink">{order.carrier}</p>
                <p className="text-sm text-ink/55">
                  Tracking number: <span className="font-medium text-ink">{order.tracking_number}</span>
                </p>
              </div>
              <span className="border border-leaf/40 bg-leaf-tint px-3 py-1 text-xs font-medium uppercase tracking-wide text-leaf">
                {order.status}
              </span>
            </div>

            <ol className="mt-8 flex items-center gap-2">
              {STATUS_STEPS.map((s, i) => (
                <li key={s} className="flex flex-1 items-center gap-2 last:flex-none">
                  <div className="flex flex-col items-center gap-1.5">
                    <span
                      className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] ${
                        i <= activeStepIndex
                          ? "bg-indigo text-parchment"
                          : "bg-ink/10 text-ink/45"
                      }`}
                    >
                      {i + 1}
                    </span>
                    <span
                      className={`text-xs capitalize ${
                        i <= activeStepIndex ? "text-ink" : "text-ink/40"
                      }`}
                    >
                      {s}
                    </span>
                  </div>
                  {i < STATUS_STEPS.length - 1 && (
                    <span
                      className={`h-px flex-1 ${
                        i < activeStepIndex ? "bg-indigo" : "bg-ink/15"
                      }`}
                    />
                  )}
                </li>
              ))}
            </ol>

            <dl className="mt-8 grid grid-cols-2 gap-4 border-t border-ink/10 pt-6 text-sm">
              <div>
                <dt className="text-ink/50">Estimated delivery</dt>
                <dd className="mt-1 font-medium text-ink">{order.estimated_delivery}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Placed</dt>
                <dd className="mt-1 font-medium text-ink">{formatDate(order.created_at)}</dd>
              </div>
              {localRecord && (
                <>
                  <div>
                    <dt className="text-ink/50">Destination</dt>
                    <dd className="mt-1 font-medium text-ink">{localRecord.destinationCity}</dd>
                  </div>
                  <div>
                    <dt className="text-ink/50">Items</dt>
                    <dd className="mt-1 font-medium text-ink">{localRecord.itemsCount}</dd>
                  </div>
                </>
              )}
            </dl>
          </div>

          {localRecord && (
            <aside className="h-fit border border-ink/10 bg-white p-6">
              <h2 className="font-display text-lg text-ink">Payment</h2>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-ink/60">Amount paid</dt>
                  <dd className="font-medium">{formatNaira(localRecord.amountNaira)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-ink/60">Reference</dt>
                  <dd className="font-medium">{localRecord.paymentId}</dd>
                </div>
              </dl>
            </aside>
          )}
        </div>
      )}

      <form onSubmit={handleLookup} className="mt-12 flex max-w-md gap-2 border-t border-ink/10 pt-8">
        <input
          value={lookup}
          onChange={(e) => setLookup(e.target.value)}
          placeholder="Look up another order ID"
          className="input"
        />
        <button
          type="submit"
          className="shrink-0 border border-indigo bg-indigo px-4 py-2.5 text-sm font-medium text-parchment hover:bg-indigo-deep"
        >
          Track
        </button>
      </form>

      <Link href="/account" className="mt-4 inline-block text-sm text-indigo-deep hover:underline">
        View all your orders
      </Link>
    </div>
  );
}
