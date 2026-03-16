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
  title: "Pikar AI | AI Agents for Business Operations — Finance, Marketing, Sales & More",
  description: "Pikar AI deploys 10 specialized AI agents that automate your finance, marketing, sales, HR, compliance, and operations 24/7. Human-in-the-loop control with enterprise-grade security.",
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
};

import { PersonaProvider } from '@/contexts/PersonaContext';
import { ChatSessionProvider } from '@/contexts/ChatSessionContext';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${outfit.variable} ${dmSans.variable} ${inter.variable} scroll-smooth`}>
      <body className="antialiased font-sans bg-background text-foreground">
        <PersonaProvider>
          <ChatSessionProvider>
            {children}
            {/* Toast notification container */}
            <Toaster
              position="top-right"
              expand={false}
              richColors
              closeButton
              duration={5000}
            />
          </ChatSessionProvider>
        </PersonaProvider>
      </body>
    </html>
  );
}
