# ShipFast Market

A realistic Nigerian ecommerce storefront (Next.js 14, TypeScript, Tailwind CSS)
built for the CipherGuard demo environment. This is **the customer-facing shop**,
not the CipherGuard security dashboard — browse products, add to cart, check
out, pay, and track delivery.

During normal development the Shop talks **directly** to the two mock
third-party services, **ShipFast** (logistics) and **PayFlex** (payments).
It never routes through Kong or CipherGuard.

## Running it

```bash
npm install
cp .env.local.example .env.local   # only needed if upstream URLs differ from the defaults
npm run dev
```

The app expects:
- ShipFast at `http://localhost:8002` (see `shop-handoff/deploy/vps-b-shipfast`)
- PayFlex at `http://localhost:8006`

Start both mock services first (each is a plain FastAPI/uvicorn app on port
`8000` inside its own container, mapped externally as above), then run the
Shop.

## How CORS is handled

ShipFast and PayFlex are thin FastAPI mocks with **no CORS headers at all**,
so a fetch straight from the browser to `http://localhost:8002/...` would be
blocked by the browser's cross-origin policy.

Instead of adding CORS to the mocks, the Shop proxies through Next.js
rewrites, configured in `next.config.js`:

```js
async rewrites() {
  return [
    { source: "/api/shipfast/:path*", destination: `${SHIPFAST_UPSTREAM_URL}/:path*` },
    { source: "/api/payflex/:path*",  destination: `${PAYFLEX_UPSTREAM_URL}/:path*` },
  ];
}
```

The browser only ever calls same-origin paths — `/api/shipfast/orders/123`,
`/api/payflex/payments/charge`, etc. (see `lib/shipfast.ts` / `lib/payflex.ts`).
Next.js's server forwards those requests to the real upstream host, so no
CORS headers are needed on ShipFast or PayFlex, and the upstream URLs never
appear in client-side code. In production, point `SHIPFAST_UPSTREAM_URL` and
`PAYFLEX_UPSTREAM_URL` (set in `.env.local` or your host's env config) at the
public `host:port` of each service — e.g. VPS B / VPS C in the multi-VPS
deployment guide.

## API surface actually used

Per `shop-handoff/docs/API.md`, only these endpoints are ever called, and only
through the rewrite proxy:

**ShipFast**
- `GET /health`
- `GET /orders/{order_id}`
- `POST /orders`
- `GET /customers/{customer_id}/address`

**PayFlex**
- `POST /payments/charge`
- `GET /payments/{payment_id}`

`/admin/internal-stats` and `/admin/vault-keys` are intentionally never
called anywhere in this codebase.

## Checkout flow

1. **Delivery details** — name, phone, email, city, address. Saved to a
   local customer profile (`lib/customer-context.tsx`, persisted to
   `localStorage`) which generates a `customer_id`. As a nice-to-have, the
   Shop calls `GET /customers/{customer_id}/address` right after this step to
   show a "delivery zone confirmed" note — purely informational, checkout
   still proceeds if it fails.
2. **Payment** — a mock card form. On submit, the Shop calls
   `POST /payments/charge` on PayFlex for the order total.
3. **Delivery booking** — once payment succeeds, the Shop calls
   `POST /orders` on ShipFast with the customer, destination city and item
   count, then redirects to `/orders/{order_id}` to show live tracking.

If payment fails, the customer can retry from the payment step. If payment
succeeds but booking delivery fails, the Shop shows the payment reference and
offers a retry that only re-attempts the ShipFast call (no double charge).

## Project structure

```
app/
  page.tsx              Home — hero + category rail + product grid
  cart/page.tsx          Basket
  checkout/page.tsx      Delivery details -> payment -> ShipFast order
  orders/[id]/page.tsx   Live tracking (GET /orders/{id})
  track/page.tsx         Standalone "track an order" entry point
  account/page.tsx       Customer profile + order history
lib/
  catalog.ts             Mocked product catalog (Shop has no backend catalog)
  shipfast.ts             ShipFast client (proxy paths only)
  payflex.ts               PayFlex client (proxy paths only)
  cart-context.tsx        Cart state, persisted to localStorage
  customer-context.tsx    Customer profile / session, persisted to localStorage
  orders-store.ts         Local order history, persisted to localStorage
components/
  ProductSwatch.tsx       Generated pattern art standing in for product photos
  ...
```

Cart, customer session and order history are all mocked client-side in
`localStorage` — ShipFast and PayFlex have no persistence or catalog of
their own, by design.
