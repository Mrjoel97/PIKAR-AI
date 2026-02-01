import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

import { Space_Grotesk, Outfit, Inter } from "next/font/google";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

import { Manrope } from "next/font/google";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
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
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} ${spaceGrotesk.variable} ${outfit.variable} ${inter.variable} ${manrope.variable} antialiased`}>
        <PersonaProvider>{children}</PersonaProvider>
      </body>
    </html>
  );
}
