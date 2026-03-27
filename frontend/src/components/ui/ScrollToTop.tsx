'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react';

export default function ScrollToTop() {
    return (
        <button
            aria-label="Back to top"
            className="glass-button fixed bottom-8 right-8 z-50 p-3 rounded-full text-primary hover:text-primary-dark transition-all hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-primary/50 group"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        >
            <span className="material-symbols-outlined text-2xl group-hover:scale-110 transition-transform">arrow_upward</span>
        </button>
    );
}
