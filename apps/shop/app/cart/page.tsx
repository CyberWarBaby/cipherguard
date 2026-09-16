"use client";

import Link from "next/link";
import { useCart } from "@/lib/cart-context";
import { getProduct } from "@/lib/catalog";
import { formatNaira } from "@/lib/format";
import ProductSwatch from "@/components/ProductSwatch";

const DELIVERY_FEE = 1500;

export default function CartPage() {
  const { items, setQty, removeItem, subtotal, totalItems } = useCart();

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-content px-4 py-20 text-center sm:px-6">
        <p className="font-display text-2xl text-ink">Your basket is empty</p>
        <p className="mt-2 text-ink/60">
          Nothing here yet — the stalls are still open.
        </p>
        <Link
          href="/"
          className="mt-6 inline-block border border-indigo bg-indigo px-5 py-3 text-sm font-medium text-parchment hover:bg-indigo-deep"
        >
          Back to shopping
        </Link>
      </div>
    );
  }

  const total = subtotal + DELIVERY_FEE;

  return (
    <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
      <h1 className="font-display text-3xl text-ink">Your basket</h1>
      <p className="mt-1 text-sm text-ink/55">
        {totalItems} item{totalItems === 1 ? "" : "s"}
      </p>

      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_320px]">
        <ul className="divide-y divide-ink/10 border-y border-ink/10">
          {items.map((item) => {
            const product = getProduct(item.productId);
            if (!product) return null;
            return (
              <li key={item.productId} className="flex gap-4 py-5">
                <div className="h-20 w-24 shrink-0 overflow-hidden border border-ink/10">
                  <ProductSwatch product={product} />
                </div>
                <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-display text-lg text-ink">{product.name}</p>
                    <p className="text-sm text-ink/55">
                      {formatNaira(product.price)} · per {product.unit}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center border border-ink/15">
                      <button
                        aria-label="Decrease quantity"
                        className="px-3 py-1.5 text-ink/70 hover:bg-parchment2"
                        onClick={() => setQty(item.productId, item.qty - 1)}
                      >
                        −
                      </button>
                      <span className="min-w-[2rem] px-1 text-center text-sm">
                        {item.qty}
                      </span>
                      <button
                        aria-label="Increase quantity"
                        className="px-3 py-1.5 text-ink/70 hover:bg-parchment2"
                        onClick={() => setQty(item.productId, item.qty + 1)}
                      >
                        +
                      </button>
                    </div>
                    <p className="w-24 text-right font-medium text-ink">
                      {formatNaira(product.price * item.qty)}
                    </p>
                    <button
                      onClick={() => removeItem(item.productId)}
                      className="text-sm text-clay hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>

        <aside className="h-fit border border-ink/10 bg-white p-6">
          <h2 className="font-display text-xl text-ink">Order summary</h2>
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-ink/60">Subtotal</dt>
              <dd>{formatNaira(subtotal)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-ink/60">Delivery (ShipFast)</dt>
              <dd>{formatNaira(DELIVERY_FEE)}</dd>
            </div>
          </dl>
          <div className="mt-4 flex justify-between border-t border-ink/10 pt-4 font-display text-lg text-ink">
            <span>Total</span>
            <span>{formatNaira(total)}</span>
          </div>
          <Link
            href="/checkout"
            className="mt-6 block w-full border border-ochre-deep bg-ochre py-3 text-center text-sm font-medium text-white hover:bg-ochre-deep"
          >
            Proceed to checkout
          </Link>
        </aside>
      </div>
    </div>
  );
}
