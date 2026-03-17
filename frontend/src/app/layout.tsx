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

export const metadata: Metadata = {
  title: "Pikar AI | Your Autonomous AI Workforce",
  description: "Deploy intelligent AI agents that research, code, and analyze your workflows 24/7. Enterprise-grade automation platform for teams that need to scale.",
  other: {
    "facebook-domain-verification": "a6wmhy1f13latfq4o4qsh8oi5rms50",
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
