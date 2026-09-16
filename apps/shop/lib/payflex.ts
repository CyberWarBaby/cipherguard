/**
 * Thin client for the PayFlex Payments mock API, called through the
 * same-origin /api/payflex/* rewrite (see next.config.js).
 *
 * Only the public surface is used:
 *   POST /payments/charge
 *   GET  /payments/{payment_id}
 * /admin/vault-keys is never called from this app.
 */

const BASE = "/api/payflex";

export interface PayFlexCharge {
  payment_id: string;
  amount: number;
  currency: string;
  customer_id: string;
  status: string;
  channel: string;
  reference: string;
  authorized_by: string;
  created_at: string;
}

export class PayFlexError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "PayFlexError";
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText || "PayFlex could not process this payment.";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // non-JSON error body, keep default detail
    }
    throw new PayFlexError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const payflex = {
  charge(payload: {
    amount: number;
    currency?: string;
    customer_id: string;
    reference?: string;
  }): Promise<PayFlexCharge> {
    return fetch(`${BASE}/payments/charge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currency: "NGN", ...payload }),
    }).then((r) => handle(r));
  },

  getPayment(paymentId: string): Promise<PayFlexCharge> {
    return fetch(`${BASE}/payments/${encodeURIComponent(paymentId)}`, {
      cache: "no-store",
    }).then((r) => handle(r));
  },
};
