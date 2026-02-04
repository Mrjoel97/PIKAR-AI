import type { Metadata } from "next";
import "./globals.css";

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
      <body className="antialiased font-sans">
        <PersonaProvider>{children}</PersonaProvider>
      </body>
    </html>
  );
}
