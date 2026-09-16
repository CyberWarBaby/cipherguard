/**
 * ShipFast Market talks directly to the ShipFast and PayFlex mock APIs during
 * normal development — never through Kong / CipherGuard. Neither upstream
 * sends CORS headers, so instead of calling http://localhost:8002 and
 * http://localhost:8006 straight from the browser, the browser calls same-origin
 * paths (/api/shipfast/*, /api/payflex/*) and Next.js rewrites them to the
 * upstream hosts server-side. No CORS headers are ever needed on ShipFast or
 * PayFlex themselves.
 *
 * In production, point these at the public host:port of each service
 * (e.g. VPS B / VPS C in the CipherGuard multi-VPS deployment guide) via
 * environment variables — see .env.local.example.
 */
const SHIPFAST_UPSTREAM_URL = process.env.SHIPFAST_UPSTREAM_URL || "http://localhost:8002";
const PAYFLEX_UPSTREAM_URL = process.env.PAYFLEX_UPSTREAM_URL || "http://localhost:8006";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/shipfast/:path*",
        destination: `${SHIPFAST_UPSTREAM_URL}/:path*`,
      },
      {
        source: "/api/payflex/:path*",
        destination: `${PAYFLEX_UPSTREAM_URL}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
