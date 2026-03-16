'use client';

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="font-display antialiased text-slate-800 bg-white min-h-screen flex flex-col relative overflow-hidden selection:bg-teal-500 selection:text-white">
      {/* Subtle background accents */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-teal-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/3" />
      </div>

      {/* Header with Logo */}
      <header className="relative z-20 w-full px-6 lg:px-12 pt-6 pb-2">
        <div className="max-w-3xl mx-auto flex items-center justify-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-600 to-teal-700 text-white flex items-center justify-center shadow-lg shadow-teal-500/25 transform -rotate-3">
              <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor" />
              </svg>
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-800 font-outfit">Pikar AI</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="relative z-10 w-full max-w-3xl mx-auto flex-grow flex flex-col">
        {children}
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full px-6 py-3 text-center text-xs text-slate-400">
        Your data is encrypted and secure
      </footer>
    </div>
  );
}
