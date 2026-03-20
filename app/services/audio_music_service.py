"""Background music selector for Director pipeline.

This intentionally keeps generation optional: it returns pre-configured URLs
from environment variables by mood and degrades to None when unavailable.
"""

import os


def select_background_music_url(mood: str | None) -> str | None:
    mood_key = (mood or "neutral").strip().lower().replace(" ", "_")
    exact_key = f"DIRECTOR_BGM_URL_{mood_key.upper()}"
    if os.getenv(exact_key):
        return os.getenv(exact_key)

    # Fallback categories
    if "upbeat" in mood_key and os.getenv("DIRECTOR_BGM_URL_UPBEAT"):
        return os.getenv("DIRECTOR_BGM_URL_UPBEAT")
    if ("calm" in mood_key or "ambient" in mood_key) and os.getenv(
        "DIRECTOR_BGM_URL_CALM"
    ):
        return os.getenv("DIRECTOR_BGM_URL_CALM")

    return os.getenv("DIRECTOR_BGM_URL_DEFAULT")
