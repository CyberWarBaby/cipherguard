"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useCustomer } from "@/lib/customer-context";
import { getOrderHistory } from "@/lib/orders-store";
import { OrderRecord } from "@/lib/types";
import { formatNaira, formatDate } from "@/lib/format";

export default function AccountPage() {
  const { profile, saveProfile } = useCustomer();
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    fullName: profile?.fullName ?? "",
    phone: profile?.phone ?? "",
    email: profile?.email ?? "",
    city: profile?.city ?? "",
    address: profile?.address ?? "",
  });

  useEffect(() => {
    setOrders(getOrderHistory());
  }, []);

  useEffect(() => {
    if (profile) {
      setForm({
        fullName: profile.fullName,
        phone: profile.phone,
        email: profile.email,
        city: profile.city,
        address: profile.address,
      });
    }
  }, [profile]);

  function handleSave(e: FormEvent) {
    e.preventDefault();
    saveProfile(form);
    setEditing(false);
  }

  return (
    <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
      <h1 className="font-display text-3xl text-ink">Your account</h1>

      <div className="mt-8 grid gap-8 lg:grid-cols-[320px_1fr]">
        <section className="h-fit border border-ink/10 bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl text-ink">Profile</h2>
            {profile && !editing && (
              <button
                onClick={() => setEditing(true)}
                className="text-sm text-indigo-deep hover:underline"
              >
                Edit
              </button>
            )}
          </div>

          {!profile && !editing && (
            <div className="mt-4">
              <p className="text-sm text-ink/60">
                No profile yet — it&rsquo;s created automatically the first time
                you check out.
              </p>
              <button
                onClick={() => setEditing(true)}
                className="mt-4 border border-indigo bg-indigo px-4 py-2 text-sm font-medium text-parchment hover:bg-indigo-deep"
              >
                Add details now
              </button>
            </div>
          )}

          {profile && !editing && (
            <dl className="mt-4 space-y-2 text-sm">
              <Row label="Name" value={profile.fullName} />
              <Row label="Phone" value={profile.phone} />
              <Row label="Email" value={profile.email} />
              <Row label="City" value={profile.city} />
              <Row label="Address" value={profile.address} />
              <Row label="Customer ID" value={profile.customerId} muted />
            </dl>
          )}

          {editing && (
            <form onSubmit={handleSave} className="mt-4 space-y-4">
              <TextField label="Full name" value={form.fullName} onChange={(v) => setForm({ ...form, fullName: v })} />
              <TextField label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
              <TextField label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} type="email" />
              <TextField label="City" value={form.city} onChange={(v) => setForm({ ...form, city: v })} />
              <TextField label="Address" value={form.address} onChange={(v) => setForm({ ...form, address: v })} />
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="border border-indigo bg-indigo px-4 py-2 text-sm font-medium text-parchment hover:bg-indigo-deep"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  className="border border-ink/15 px-4 py-2 text-sm text-ink/70 hover:bg-parchment2"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </section>

        <section>
          <h2 className="font-display text-xl text-ink">Order history</h2>
          {orders.length === 0 ? (
            <div className="mt-4 border border-ink/10 bg-white p-8 text-center">
              <p className="text-ink/60">No orders yet.</p>
              <Link href="/" className="mt-3 inline-block text-sm text-indigo-deep hover:underline">
                Start shopping
              </Link>
            </div>
          ) : (
            <ul className="mt-4 divide-y divide-ink/10 border-y border-ink/10">
              {orders.map((o) => (
                <li key={o.localId} className="flex flex-wrap items-center justify-between gap-3 py-4">
                  <div>
                    <p className="font-medium text-ink">{o.trackingNumber}</p>
                    <p className="text-sm text-ink/55">
                      {formatDate(o.createdAt)} · {o.destinationCity} · {o.itemsCount} item
                      {o.itemsCount === 1 ? "" : "s"}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <p className="font-medium text-ink">{formatNaira(o.amountNaira)}</p>
                    <Link
                      href={`/orders/${o.shipfastOrderId}`}
                      className="border border-indigo/30 px-3 py-1.5 text-sm text-indigo-deep hover:border-indigo"
                    >
                      Track
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function Row({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink/50">{label}</dt>
      <dd className={muted ? "text-ink/40" : "text-ink"}>{value}</dd>
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm text-ink/70">{label}</span>
      <input
        required
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input"
      />
    </label>
  );
}
