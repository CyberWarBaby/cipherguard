"use client";

import { FormEvent, ReactNode, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "@/lib/cart-context";
import { useCustomer } from "@/lib/customer-context";
import { getProduct } from "@/lib/catalog";
import { formatNaira, shortId } from "@/lib/format";
import { shipfast, ShipFastError } from "@/lib/shipfast";
import { payflex, PayFlexError, PayFlexCharge } from "@/lib/payflex";
import { saveOrder } from "@/lib/orders-store";

const DELIVERY_FEE = 1500;
const CITIES = [
  "Lagos",
  "Abuja",
  "Port Harcourt",
  "Ibadan",
  "Kano",
  "Enugu",
  "Benin City",
  "Kaduna",
];

type Step = "details" | "payment" | "placing" | "error";

export default function CheckoutPage() {
  const router = useRouter();
  const { items, subtotal, totalItems, clear } = useCart();
  const { profile, saveProfile } = useCustomer();

  const [step, setStep] = useState<Step>("details");
  const [zoneNote, setZoneNote] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [paidCharge, setPaidCharge] = useState<PayFlexCharge | null>(null);

  const [details, setDetails] = useState({
    fullName: profile?.fullName ?? "",
    phone: profile?.phone ?? "",
    email: profile?.email ?? "",
    city: profile?.city ?? CITIES[0],
    address: profile?.address ?? "",
  });

  const [card, setCard] = useState({
    name: "",
    number: "",
    expiry: "",
    cvv: "",
  });

  const total = subtotal + DELIVERY_FEE;

  const lineItems = useMemo(
    () =>
      items
        .map((i) => ({ item: i, product: getProduct(i.productId) }))
        .filter((x) => x.product),
    [items]
  );

  if (items.length === 0 && step === "details") {
    return (
      <div className="mx-auto max-w-content px-4 py-20 text-center sm:px-6">
        <p className="font-display text-2xl text-ink">
          Your basket is empty
        </p>
        <p className="mt-2 text-ink/60">Add something to the basket before checking out.</p>
      </div>
    );
  }

  async function handleDetailsSubmit(e: FormEvent) {
    e.preventDefault();
    const saved = saveProfile(details);
    // Best-effort: confirm ShipFast can resolve a delivery zone for this
    // customer. Purely informational — checkout still proceeds if this fails.
    try {
      const addr = await shipfast.getCustomerAddress(saved.customerId);
      setZoneNote(`Delivery zone confirmed: ${addr.city}, ${addr.country}.`);
    } catch {
      setZoneNote(null);
    }
    setStep("payment");
  }

  async function handlePaymentSubmit(e: FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    setStep("placing");

    const customerId = profile?.customerId ?? saveProfile(details).customerId;

    try {
      const charge = await payflex.charge({
        amount: total,
        currency: "NGN",
        customer_id: customerId,
        reference: shortId("chk"),
      });
      setPaidCharge(charge);
      await createShippingOrder(charge, customerId);
    } catch (err) {
      setStep("error");
      if (err instanceof PayFlexError) {
        setErrorMessage(
          `Payment didn't go through — ${err.message}. Check the card details and try again.`
        );
      } else {
        setErrorMessage("Payment didn't go through. Check the card details and try again.");
      }
    }
  }

  async function createShippingOrder(charge: PayFlexCharge, customerId: string) {
    try {
      const order = await shipfast.createOrder({
        customer_id: customerId,
        destination_city: details.city,
        items_count: totalItems,
      });
      saveOrder({
        localId: shortId("loc"),
        shipfastOrderId: order.order_id,
        paymentId: charge.payment_id,
        trackingNumber: order.tracking_number,
        carrier: order.carrier,
        status: order.status,
        estimatedDelivery: order.estimated_delivery,
        amountNaira: total,
        itemsCount: totalItems,
        destinationCity: details.city,
        createdAt: order.created_at,
      });
      clear();
      router.push(`/orders/${order.order_id}`);
    } catch (err) {
      setStep("error");
      if (err instanceof ShipFastError) {
        setErrorMessage(
          `Payment of ${formatNaira(total)} was received (ref ${charge.payment_id}), but we couldn't book delivery — ${err.message}. Try again, or keep this reference for support.`
        );
      } else {
        setErrorMessage(
          `Payment of ${formatNaira(total)} was received (ref ${charge.payment_id}), but we couldn't book delivery. Try again, or keep this reference for support.`
        );
      }
    }
  }

  async function retryShipping() {
    if (!paidCharge) {
      setStep("payment");
      return;
    }
    const customerId = profile?.customerId ?? saveProfile(details).customerId;
    setErrorMessage(null);
    setStep("placing");
    await createShippingOrder(paidCharge, customerId);
  }

  return (
    <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
      <h1 className="font-display text-3xl text-ink">Checkout</h1>
      <Steps current={step} />

      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_320px]">
        <div>
          {step === "details" && (
            <form onSubmit={handleDetailsSubmit} className="space-y-5 border border-ink/10 bg-white p-6">
              <h2 className="font-display text-xl text-ink">Delivery details</h2>
              <Field label="Full name">
                <input
                  required
                  value={details.fullName}
                  onChange={(e) => setDetails({ ...details, fullName: e.target.value })}
                  className="input"
                  placeholder="Chidinma Okafor"
                />
              </Field>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Phone number">
                  <input
                    required
                    value={details.phone}
                    onChange={(e) => setDetails({ ...details, phone: e.target.value })}
                    className="input"
                    placeholder="080X XXX XXXX"
                  />
                </Field>
                <Field label="Email">
                  <input
                    required
                    type="email"
                    value={details.email}
                    onChange={(e) => setDetails({ ...details, email: e.target.value })}
                    className="input"
                    placeholder="you@example.com"
                  />
                </Field>
              </div>
              <Field label="City">
                <select
                  value={details.city}
                  onChange={(e) => setDetails({ ...details, city: e.target.value })}
                  className="input"
                >
                  {CITIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Delivery address">
                <textarea
                  required
                  value={details.address}
                  onChange={(e) => setDetails({ ...details, address: e.target.value })}
                  className="input min-h-[80px]"
                  placeholder="Street, house number, landmark"
                />
              </Field>
              <button
                type="submit"
                className="w-full border border-indigo bg-indigo py-3 text-sm font-medium text-parchment hover:bg-indigo-deep"
              >
                Continue to payment
              </button>
            </form>
          )}

          {step === "payment" && (
            <form onSubmit={handlePaymentSubmit} className="space-y-5 border border-ink/10 bg-white p-6">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl text-ink">Payment</h2>
                <button
                  type="button"
                  onClick={() => setStep("details")}
                  className="text-sm text-indigo-deep hover:underline"
                >
                  Edit delivery details
                </button>
              </div>
              {zoneNote && (
                <p className="border border-leaf/30 bg-leaf-tint px-3 py-2 text-sm text-leaf">
                  {zoneNote}
                </p>
              )}
              <Field label="Name on card">
                <input
                  required
                  value={card.name}
                  onChange={(e) => setCard({ ...card, name: e.target.value })}
                  className="input"
                  placeholder="As shown on card"
                />
              </Field>
              <Field label="Card number">
                <input
                  required
                  inputMode="numeric"
                  maxLength={19}
                  value={card.number}
                  onChange={(e) => setCard({ ...card, number: e.target.value })}
                  className="input"
                  placeholder="4111 1111 1111 1111"
                />
              </Field>
              <div className="grid grid-cols-2 gap-5">
                <Field label="Expiry">
                  <input
                    required
                    value={card.expiry}
                    onChange={(e) => setCard({ ...card, expiry: e.target.value })}
                    className="input"
                    placeholder="MM/YY"
                  />
                </Field>
                <Field label="CVV">
                  <input
                    required
                    inputMode="numeric"
                    maxLength={4}
                    value={card.cvv}
                    onChange={(e) => setCard({ ...card, cvv: e.target.value })}
                    className="input"
                    placeholder="123"
                  />
                </Field>
              </div>
              <button
                type="submit"
                className="w-full border border-ochre-deep bg-ochre py-3 text-sm font-medium text-white hover:bg-ochre-deep"
              >
                Pay {formatNaira(total)}
              </button>
              <p className="text-xs text-ink/45">
                This is a demo checkout. Card details are sent only to the PayFlex
                sandbox and are not stored.
              </p>
            </form>
          )}

          {step === "placing" && (
            <div className="border border-ink/10 bg-white p-10 text-center">
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-indigo/30 border-t-indigo" />
              <p className="mt-4 font-display text-lg text-ink">
                {paidCharge ? "Booking your delivery…" : "Processing payment…"}
              </p>
            </div>
          )}

          {step === "error" && (
            <div className="space-y-4 border border-clay/30 bg-clay-tint p-6">
              <h2 className="font-display text-xl text-clay">Something needs your attention</h2>
              <p className="text-sm text-ink/80">{errorMessage}</p>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={paidCharge ? retryShipping : () => setStep("payment")}
                  className="border border-indigo bg-indigo px-4 py-2 text-sm font-medium text-parchment hover:bg-indigo-deep"
                >
                  {paidCharge ? "Retry booking delivery" : "Back to payment"}
                </button>
              </div>
            </div>
          )}
        </div>

        <aside className="h-fit border border-ink/10 bg-white p-6">
          <h2 className="font-display text-xl text-ink">Order summary</h2>
          <ul className="mt-4 space-y-3 text-sm">
            {lineItems.map(({ item, product }) => (
              <li key={item.productId} className="flex justify-between gap-3">
                <span className="text-ink/70">
                  {product!.name} × {item.qty}
                </span>
                <span>{formatNaira(product!.price * item.qty)}</span>
              </li>
            ))}
          </ul>
          <dl className="mt-4 space-y-2 border-t border-ink/10 pt-4 text-sm">
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
        </aside>
      </div>
    </div>
  );
}

function Steps({ current }: { current: Step }) {
  const order: { key: Step[]; label: string }[] = [
    { key: ["details"], label: "Delivery" },
    { key: ["payment"], label: "Payment" },
    { key: ["placing", "error"], label: "Confirmation" },
  ];
  return (
    <div className="mt-4 flex items-center gap-3 text-sm">
      {order.map((s, i) => {
        const active = s.key.includes(current);
        return (
          <div key={s.label} className="flex items-center gap-3">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                active ? "bg-indigo text-parchment" : "bg-ink/10 text-ink/50"
              }`}
            >
              {i + 1}
            </span>
            <span className={active ? "text-ink" : "text-ink/45"}>{s.label}</span>
            {i < order.length - 1 && <span className="h-px w-8 bg-ink/15" />}
          </div>
        );
      })}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm text-ink/70">{label}</span>
      {children}
    </label>
  );
}
