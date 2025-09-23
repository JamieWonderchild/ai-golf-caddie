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
    
    # Extract handicap first to avoid confusion with distance
    handicap_mentioned = _extract_handicap_mention(text_l)
    
    # distance like "150 yards" or "150y" or "at 150" 
    # BUT avoid matching numbers that are part of handicap mentions
    distance = None
    distance_patterns = [
        r"(\d{2,3})\s*(?:yard|yards|y|yd|yds)\b",  # Require yard-related suffix
        r"\bat\s+(\d{2,3})\b",  # "at 150"  
        r"(\d{2,3})\s*(?:yard|yards)\s+(?:par|hole)",  # "161 yard par three"
    ]
    
    for pattern in distance_patterns:
        m = re.search(pattern, text_l)
        if m:
            potential_distance = int(m.group(1))
            # Avoid distances that are likely handicaps (under 36)
            if potential_distance > 36:  # Reasonable minimum golf shot distance
                distance = potential_distance
                break

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
    # Club patterns to look for (including word numbers)
    club_patterns = [
        r"\b(driver|drive)\b",
        r"\b(\d+)\s*wood\b",
        r"\b(three|four|five|six|seven|eight|nine)\s*wood\b",
        r"\b(\d+)\s*iron\b", 
        r"\b(three|four|five|six|seven|eight|nine)\s*iron\b",
        r"\b(pitching\s*wedge|pw)\b",
        r"\b(sand\s*wedge|sw)\b",
        r"\b(lob\s*wedge|lw)\b",
        r"\b(gap\s*wedge|gw)\b",
        r"\b(wedge)\b",
        r"\b(putter|putt)\b",
    ]
    
    # Word to number mapping for clubs
    word_to_num = {'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9}
    
    for pattern in club_patterns:
        match = re.search(pattern, text_l)
        if match:
            # Normalize club names
            full_match = match.group(0)
            if "driver" in full_match or "drive" in full_match:
                return "driver"
            elif "wood" in full_match:
                # Check for word numbers first
                for word, num in word_to_num.items():
                    if word in full_match:
                        return f"{num}-wood"
                # Fall back to digit
                number = re.search(r"(\d+)", full_match)
                return f"{number.group(1)}-wood" if number else "3-wood"
            elif "iron" in full_match:
                # Check for word numbers first  
                for word, num in word_to_num.items():
                    if word in full_match:
                        return f"{num}-iron"
                # Fall back to digit
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
    # Word to number mapping for spoken numbers
    word_to_num = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'scratch': 0
    }
    
    # Handicap patterns - both digits and words
    handicap_patterns = [
        r"\bi'?m\s+a\s+(\d{1,2})\s+handicap\b",
        r"\bi'?m\s+a\s+(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+handicap\b",
        r"\bmy\s+handicap\s+is\s+(\d{1,2})\b",
        r"\bmy\s+handicap\s+is\s+(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b",
        r"\b(\d{1,2})\s+handicap\s+player\b",
        r"\bhandicap\s+(\d{1,2})\b",
        r"\bhandicap\s+(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b",
        r"\bi\s+play\s+to\s+a?\s+(\d{1,2})\b",
        r"\bi'?m\s+a\s+(\d{1,2})\b",  # Less specific but common
        r"\bi'?m\s+a\s+(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b",
        r"\bscratch\s+golfer\b",  # Special case for scratch
        r"\bscratch\s+player\b",
    ]
    
    for pattern in handicap_patterns:
        match = re.search(pattern, text_l)
        if match:
            if "scratch" in pattern:
                return 0
            try:
                matched_text = match.group(1)
                # Try to convert word to number first
                if matched_text in word_to_num:
                    handicap = word_to_num[matched_text]
                else:
                    # Fall back to digit parsing
                    handicap = int(matched_text)
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


