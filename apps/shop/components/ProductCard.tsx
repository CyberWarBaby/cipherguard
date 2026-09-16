"use client";

import { useState } from "react";
import { Product } from "@/lib/types";
import { formatNaira } from "@/lib/format";
import { useCart } from "@/lib/cart-context";
import ProductSwatch from "./ProductSwatch";
import Stars from "./Stars";

export default function ProductCard({ product }: { product: Product }) {
  const { addItem } = useCart();
  const [justAdded, setJustAdded] = useState(false);

  function handleAdd() {
    addItem(product.id, 1);
    setJustAdded(true);
    window.setTimeout(() => setJustAdded(false), 1400);
  }

  return (
    <div className="flex flex-col border border-ink/10 bg-white">
      <div className="aspect-[5/4] w-full overflow-hidden">
        <ProductSwatch product={product} />
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="font-display text-[17px] leading-snug text-ink">
          {product.name}
        </h3>
        <div className="flex items-center gap-2 text-xs text-ink/60">
          <Stars rating={product.rating} />
          <span>({product.reviews})</span>
        </div>
        <p className="line-clamp-2 text-sm text-ink/65">{product.description}</p>
        <div className="mt-auto flex items-end justify-between pt-3">
          <div>
            <p className="font-display text-lg text-indigo-deep">
              {formatNaira(product.price)}
            </p>
            <p className="text-xs text-ink/50">per {product.unit}</p>
          </div>
          <button
            onClick={handleAdd}
            className="border border-indigo bg-indigo px-3 py-2 text-xs font-medium tracking-wide text-parchment transition-colors hover:bg-indigo-deep"
          >
            {justAdded ? "Added ✓" : "Add to cart"}
          </button>
        </div>
      </div>
    </div>
  );
}
