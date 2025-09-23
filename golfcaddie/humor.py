from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class HumorContext:
    handicap: int
    distance_yards: int
    lie: str
    hazards: List[str]
    recommended_club: str
    shot_type: str
    aim_offset_yards: int
    confidence: float
    go_to_hint: Optional[str] = None


def _ambition_gap(handicap: int, distance_yards: int, recommended_club: str) -> str:
    # Rough heuristic: long irons/woods beyond 180y for 20+ handicap → high ambition
    if handicap >= 20 and recommended_club in {"3w", "5i"} and distance_yards >= 180:
        return "high"
    if handicap >= 15 and distance_yards >= 170:
        return "medium"
    return "low"


def generate_humor(ctx: HumorContext, use_llm: bool = False) -> str:
    ambition = _ambition_gap(ctx.handicap, ctx.distance_yards, ctx.recommended_club)
    parts: List[str] = []

    # Opening quip
    if ambition == "high":
        parts.append("Ambitious. I respect the confidence—let's also respect the water hazard.")
    elif ambition == "medium":
        parts.append("Bold choice. Let's give it a smart target and keep the story short.")
    else:
        parts.append("Sensible play. Boring golf is underrated—and lower scoring.")

    # Rationale snippet
    rationale = f"{ctx.recommended_club} with a {ctx.shot_type}"
    if ctx.aim_offset_yards:
        direction = "right" if ctx.aim_offset_yards > 0 else "left"
        rationale += f", aim {abs(ctx.aim_offset_yards)} yards {direction}"
    parts.append(rationale + ".")

    # Go-to hint
    if ctx.go_to_hint:
        parts.append(f"This matches your go‑to: {ctx.go_to_hint}.")

    # Hazard nudge
    if ctx.hazards:
        parts.append("Eyes up for " + ", ".join(ctx.hazards) + ".")

    # Confidence-based sign-off
    if ctx.confidence >= 0.75:
        parts.append("Green light. Commit and swing smooth.")
    elif ctx.confidence >= 0.5:
        parts.append("Looks good—tempo first, heroics second.")
    else:
        parts.append("Play the percentages and we’ll be telling a happier story.")

    return " " .join(parts)


