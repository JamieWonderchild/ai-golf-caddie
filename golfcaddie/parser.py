from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


LIES = ["fairway", "rough", "sand", "bunker", "tee"]
HAZARDS = ["water", "bunker", "trees", "woods", "pond"]


@dataclass
class ParsedIntent:
    distance_yards: Optional[int]
    lie: str
    hazards: List[str]
    club_mentioned: Optional[str] = None
    validation_warning: Optional[str] = None
    handicap_mentioned: Optional[int] = None


def parse_intent(text: str, handicap: Optional[int] = None) -> ParsedIntent:
    text_l = text.lower()
    # distance like "150 yards" or "150y" or "at 150"
    m = re.search(r"(\d{2,3})\s*(?:y|yd|yds|yards)?\b", text_l)
    distance = int(m.group(1)) if m else None

    lie = "fairway"
    for cand in LIES:
        if cand in text_l:
            # map bunker to sand
            lie = "sand" if cand in {"sand", "bunker"} else cand
            break

    hazards: List[str] = []
    for hz in HAZARDS:
        if hz in text_l and (hz != lie):
            hazards.append(hz if hz != "bunker" else "front_bunker")

    # Extract club mentions
    club_mentioned = _extract_club_mention(text_l)
    
    # Extract handicap mentions
    handicap_mentioned = _extract_handicap_mention(text_l)
    
    # Use mentioned handicap if available, otherwise fall back to provided handicap
    effective_handicap = handicap_mentioned if handicap_mentioned is not None else handicap
    
    # Validate distance/club combination if both are provided
    validation_warning = None
    if effective_handicap is not None and club_mentioned and distance:
        validation_warning = _validate_distance_club_combination(effective_handicap, club_mentioned, distance)

    return ParsedIntent(
        distance_yards=distance, 
        lie=lie, 
        hazards=hazards,
        club_mentioned=club_mentioned,
        validation_warning=validation_warning,
        handicap_mentioned=handicap_mentioned
    )


def _extract_club_mention(text_l: str) -> Optional[str]:
    """Extract club mentions from text."""
    # Club patterns to look for
    club_patterns = [
        r"\b(driver|drive)\b",
        r"\b(\d+)\s*wood\b",
        r"\b(\d+)\s*iron\b",
        r"\b(pitching\s*wedge|pw)\b",
        r"\b(sand\s*wedge|sw)\b",
        r"\b(lob\s*wedge|lw)\b",
        r"\b(gap\s*wedge|gw)\b",
        r"\b(wedge)\b",
        r"\b(putter|putt)\b",
    ]
    
    for pattern in club_patterns:
        match = re.search(pattern, text_l)
        if match:
            # Normalize club names
            full_match = match.group(0)
            if "driver" in full_match or "drive" in full_match:
                return "driver"
            elif "wood" in full_match:
                number = re.search(r"(\d+)", full_match)
                return f"{number.group(1)}-wood" if number else "3-wood"
            elif "iron" in full_match:
                number = re.search(r"(\d+)", full_match)
                return f"{number.group(1)}-iron" if number else "7-iron"
            elif "pitching" in full_match or "pw" in full_match:
                return "pitching-wedge"
            elif "sand" in full_match or "sw" in full_match:
                return "sand-wedge"
            elif "lob" in full_match or "lw" in full_match:
                return "lob-wedge"
            elif "gap" in full_match or "gw" in full_match:
                return "gap-wedge"
            elif "wedge" in full_match:
                return "pitching-wedge"  # Default wedge
            elif "putter" in full_match or "putt" in full_match:
                return "putter"
    
    return None


def _extract_handicap_mention(text_l: str) -> Optional[int]:
    """Extract handicap mentions from text."""
    # Handicap patterns to look for
    handicap_patterns = [
        r"\bi'?m\s+a\s+(\d{1,2})\s+handicap\b",
        r"\bmy\s+handicap\s+is\s+(\d{1,2})\b",
        r"\b(\d{1,2})\s+handicap\s+player\b",
        r"\bhandicap\s+(\d{1,2})\b",
        r"\bi\s+play\s+to\s+a?\s+(\d{1,2})\b",
        r"\bi'?m\s+a\s+(\d{1,2})\b",  # Less specific but common
        r"\bscratch\s+golfer\b",  # Special case for scratch
        r"\bscratch\s+player\b",
    ]
    
    for pattern in handicap_patterns:
        match = re.search(pattern, text_l)
        if match:
            if "scratch" in pattern:
                return 0
            try:
                handicap = int(match.group(1))
                # Clamp to reasonable range
                return max(0, min(30, handicap))
            except (ValueError, IndexError):
                continue
    
    return None


def _validate_distance_club_combination(handicap: int, club: str, distance: int) -> Optional[str]:
    """Validate if distance/club combination is realistic for handicap."""
    try:
        from .statistics import get_golf_statistics
        golf_stats = get_golf_statistics()
        is_valid, reason = golf_stats.validate_distance_claim(handicap, club, distance)
        return None if is_valid else reason
    except Exception:
        # Fail gracefully if statistics module isn't available
        return None


