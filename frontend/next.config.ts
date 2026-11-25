import type { NextConfig } from "next";

// The browser calls /api/* on the same origin; Next proxies to the FastAPI backend.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8010";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    // Workspace pages render in the browser only (BrowserOnly in app-shell.tsx), so the default
    // implicit instant-navigation check fails on every route ("Could not validate `instant`").
    // Validate only segments that explicitly export `instant`.
    instantInsights: { validationLevel: "manual-warning" },
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
