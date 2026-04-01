import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const configDir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Turbopack resolves CSS @import "tailwindcss" from the repo root
  // (because a root package.json exists). Explicitly alias tailwindcss
  // to the frontend node_modules so it resolves correctly.
  turbopack: {
    resolveAlias: {
      tailwindcss: path.join(configDir, 'node_modules', 'tailwindcss'),
    },
  },

  // React Compiler for automatic memoization (React 19+)
  reactCompiler: true,

  // Optimize images from external sources
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
      },
    ],
    // Use modern formats for smaller sizes
    formats: ['image/avif', 'image/webp'],
    // Cache optimized images for 1 hour to avoid re-fetching on every request
    minimumCacheTTL: 3600,
    // Skip image optimization in development to avoid upstream timeout errors
    // and reduce dev server load. Images are served directly from the source.
    unoptimized: process.env.NODE_ENV === 'development',
  },

  // Reduce bundle size by tree-shaking large packages
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
    },
  },

  // Enable compression
  compress: true,

  // Strict mode for catching issues early
  reactStrictMode: true,

  // Reduce unnecessary powered-by header
  poweredByHeader: false,

  // Expose NEXT_PUBLIC_API_URL to the client bundle explicitly.
  // Turbopack may not inline process.env.NEXT_PUBLIC_* in all cases.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
  },
};

export default nextConfig;
