// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import type { Metadata } from "next";
import { Outfit, DM_Sans, Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from 'sonner';

// Font Configuration - Only load fonts that are actually used
// Removed: Syne (unused across entire codebase)
const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: 'swap',
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: 'swap',
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: 'swap',
});

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover' as const,
  interactiveWidget: 'resizes-content' as const,
};

export const metadata: Metadata = {
  title: "Pikar AI | AI Agents for Business Operations",
  description: "10 specialized AI agents automate finance, marketing, sales, HR, and operations 24/7. Human-in-the-loop control with enterprise-grade security.",
  keywords: ["AI agents", "AI automation", "business operations AI", "AI workforce", "workflow automation", "AI for business"],
  openGraph: {
    title: "Pikar AI | Your Autonomous AI Workforce",
    description: "10 specialized AI agents that handle finance, marketing, sales, HR, compliance, and operations around the clock.",
    url: "https://pikar.ai",
    siteName: "Pikar AI",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Pikar AI | Your Autonomous AI Workforce",
    description: "10 specialized AI agents that handle finance, marketing, sales, HR, compliance, and operations around the clock.",
  },
  alternates: {
    canonical: "https://pikar.ai",
  },
  robots: {
    index: true,
    follow: true,
  },
  other: {
    "facebook-domain-verification": "a6wmhy1f13latfq4o4qsh8oi5rms50",
  },
};

import { PersonaProvider } from '@/contexts/PersonaContext';
import { SessionMapProvider } from '@/contexts/SessionMapContext';
import { SessionControlProvider } from '@/contexts/SessionControlContext';
import SessionMonitor from '@/components/SessionMonitor';
import AbortErrorSilencer from '@/components/AbortErrorSilencer';
import CookieConsent from '@/components/CookieConsent';
import { RootErrorBoundary } from '@/components/errors/RootErrorBoundary';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${outfit.variable} ${dmSans.variable} ${inter.variable} scroll-smooth`}>
      <head>
        {/* Plain <script> (not next/script) so it renders as a real
            synchronous tag in the HTML head and executes before any other
            script — silences extension promise noise that fires during
            initial page load. next/script's beforeInteractive strategy in
            App Router only preloads + runs client-side post-hydration. */}
        <script src="/silence-extension-noise.js" />
      </head>
      <body className="antialiased font-sans bg-background text-foreground">
        {/* Outermost layout-level error boundary — catches render errors from
            providers and all descendants so a single broken client component
            never blanks the screen. See plan 49-02 (AUTH-02). */}
        <RootErrorBoundary>
          <AbortErrorSilencer />
          <PersonaProvider>
            <SessionMonitor />
            <SessionMapProvider>
              <SessionControlProvider>
                {children}
                {/* GDPR cookie consent banner — must appear on every page */}
                <CookieConsent />
                {/* Toast notification container */}
                <Toaster
                  position="top-right"
                  expand={false}
                  richColors
                  closeButton
                  duration={5000}
                />
              </SessionControlProvider>
            </SessionMapProvider>
          </PersonaProvider>
        </RootErrorBoundary>
      </body>
    </html>
  );
}
