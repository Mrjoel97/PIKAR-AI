# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Backward compatibility module for Supabase client.

This module provides backward compatibility by re-exporting from the
new unified supabase_client module. All code should migrate to using
app.services.supabase_client directly.
"""

import os
import warnings

if os.getenv("PIKAR_ENABLE_DEPRECATED_IMPORT_WARNINGS") == "1":
    warnings.warn(
        "app.services.supabase is deprecated, use app.services.supabase_client instead",
        DeprecationWarning,
        stacklevel=2,
    )

from app.services.supabase_client import (
    AsyncSupabaseService,
    SupabaseService,
    get_anon_client,
    get_async_anon_client,
    get_async_client,
    get_async_service,
    get_client,
    get_client_stats,
    get_service_client,
    get_supabase_client,
    get_supabase_service,
    invalidate_client,
)

__all__ = [
    "AsyncSupabaseService",
    "SupabaseService",
    "get_anon_client",
    "get_async_anon_client",
    "get_async_client",
    "get_async_service",
    "get_client",
    "get_client_stats",
    "get_service_client",
    "get_supabase_client",
    "get_supabase_service",
    "invalidate_client",
]
