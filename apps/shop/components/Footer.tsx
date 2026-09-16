export default function Footer() {
  return (
    <footer className="mt-16 border-t border-ink/10 bg-indigo-deep text-parchment/80">
      <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-3">
          <div>
            <p className="font-display text-xl text-parchment">ShipFast Market</p>
            <p className="mt-2 max-w-xs text-sm text-parchment/60">
              Fabric, food, gadgets and more from vetted local sellers, delivered
              across Nigeria.
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-parchment">We deliver to</p>
            <p className="mt-2 text-sm text-parchment/60">
              Lagos · Abuja · Port Harcourt · Ibadan · Kano · Enugu, and every
              state ShipFast Logistics reaches.
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-parchment">Payments</p>
            <p className="mt-2 text-sm text-parchment/60">
              Card and bank transfer, processed securely by PayFlex. Pay on
              delivery coming soon.
            </p>
          </div>
        </div>
        <p className="mt-10 border-t border-parchment/15 pt-6 text-xs text-parchment/45">
          © {new Date().getFullYear()} ShipFast Market. A demo storefront.
        </p>
      </div>
    </footer>
  );
}
