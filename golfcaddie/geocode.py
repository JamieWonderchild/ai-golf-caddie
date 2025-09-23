from __future__ import annotations

import re
import httpx
from typing import Tuple


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def extract_course_name(transcript: str) -> str:
    """Heuristic extraction of course name from a natural language request.

    Examples:
      "I'm on the first tee of Finchley Golf Club. Please give me a weather report"
      -> "Finchley Golf Club"
    """
    text = transcript.strip()
    # Normalize spaces
    text = re.sub(r"\s+", " ", text)
    lower = text.lower()

    # Prefer phrase after "first tee of"
    m = re.search(r"\bfirst tee of\s+(.+)", lower)
    start_idx = None
    if m:
        start_idx = m.start(1)
    else:
        # Next: after " at "
        m2 = re.search(r"\bat\s+(.+)", lower)
        if m2:
            start_idx = m2.start(1)
        else:
            # Fallback: after " of "
            of_idx = lower.find(" of ")
            if of_idx != -1:
                start_idx = of_idx + 4

    if start_idx is None:
        # As a last resort, use entire text
        candidate = text
    else:
        candidate = text[start_idx:]

    # Stop at common trailing phrases
    candidate = re.split(r"(?i)please|give me|weather|report|conditions|what are|today|now|current", candidate)[0]
    # Trim punctuation
    candidate = candidate.strip(" .,!?")
    return candidate.strip()


def geocode_course(query: str, *, user_agent: str = "golfcaddie/1.0") -> Tuple[float, float]:
    """Geocode a golf course or location string using OSM Nominatim.

    Returns (lat, lon) as floats. Raises ValueError if not found.
    """
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": user_agent}
    print(f"[GEOCODE] GET {NOMINATIM_URL} params={params}")
    with httpx.Client(timeout=10.0, headers=headers) as client:
        resp = client.get(NOMINATIM_URL, params=params)
        print(f"[GEOCODE] status={resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError(f"No results for query: {query}")
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        print(f"[GEOCODE] result lat={lat} lon={lon}")
        return lat, lon


