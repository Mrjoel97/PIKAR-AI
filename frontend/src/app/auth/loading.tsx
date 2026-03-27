// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export default function AuthLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f6f8f8]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-3 border-teal-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-500 animate-pulse">Loading...</p>
      </div>
    </div>
  );
}
