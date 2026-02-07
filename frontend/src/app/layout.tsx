import type { Metadata } from "next";
import { Outfit, DM_Sans, Inter, Syne } from "next/font/google";
import "./globals.css";
import { Toaster } from 'sonner';

// Font Configuration
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

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  display: 'swap',
});

export const metadata: Metadata = {
  title: "Pikar AI | Your Autonomous AI Workforce",
  description: "Deploy intelligent AI agents that research, code, and analyze your workflows 24/7. Enterprise-grade automation platform for teams that need to scale.",
};

import { PersonaProvider } from '@/contexts/PersonaContext';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${outfit.variable} ${dmSans.variable} ${inter.variable} ${syne.variable} scroll-smooth`}>
      <body className="antialiased font-sans bg-background text-foreground">
        <PersonaProvider>
          {children}
          {/* Toast notification container */}
          <Toaster
            position="top-right"
            expand={false}
            richColors
            closeButton
            duration={5000}
          />
        </PersonaProvider>
      </body>
    </html>
  );
}
