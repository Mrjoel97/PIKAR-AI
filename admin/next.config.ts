import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // React Compiler for automatic memoization (React 19+)
  reactCompiler: true,

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

  // Remove powered-by header
  poweredByHeader: false,
};

export default nextConfig;
