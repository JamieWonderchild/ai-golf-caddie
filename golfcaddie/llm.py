from __future__ import annotations

import os
import re
from typing import Optional

from openai import OpenAI
from .statistics import get_golf_statistics
from .parser import parse_intent


def build_prompt(
    transcript: str,
    handicap: int,
    lat: float,
    lon: float,
    bearing: int,
    history: list[tuple[str, str]] | None = None,
    conditions: str | None = None,
    hole_layout: str | None = None,
) -> str:
    history_block = ""
    humor_hint = ""
    if history:
        last = history[-3:]
        lines = []
        for i, (said, reply) in enumerate(last, 1):
            lines.append(f"- Shot {i}: user='{said[:140]}', caddie='{reply[:140]}'")
        history_block = "Recent shots (use for context, but don't repeat):\n" + "\n".join(lines) + "\n\n"

        # Lightweight tone tweak based on the very last shot text
        last_user, _last_reply = history[-1]
        bad_words = ["shank", "slice", "hook", "chunk", "duff", "top", "water", "out of bounds", "OB"]
        if any(w in last_user.lower() for w in bad_words):
            humor_hint = (
                "- If the previous shot mentions a mishit (shank/slice/hook/chunk/top/water/OB), add a playful one-line roast acknowledging it.\n"
            )

    conditions_block = (f"Current conditions: {conditions}\n" if conditions else "")
    hole_block = (f"Hole layout: {hole_layout}\n" if hole_layout else "")
    
    # Add golf statistics context
    stats_block = _build_statistics_context(transcript, handicap)

    return (
        "You are a witty, sarcastic but helpful golf caddie.\n"
        + history_block
        + "Task: Based on the user's transcript and metadata, choose an appropriate club and shot.\n"
        "Instructions:\n"
        "- Do NOT default to the same club each time (avoid always suggesting 7-iron).\n"
        "- Consider distance, lie, hazards, handicap and risk tolerance.\n"
        "- Use the performance data below to give realistic recommendations for this handicap level.\n"
        "- If uncertain, pick the most playable safe option for the handicap.\n"
        "- Keep it concise and specific.\n"
        + humor_hint +
        "Output (<= 2 sentences):\n"
        "1) Club + shot type + simple aim note if needed + reason as to why.\n"
        "2) Two short humorous sentence.\n\n"
        + conditions_block + hole_block + stats_block +
        f"Transcript: {transcript}\n"
        f"Handicap: {handicap}\n"
        f"Location: lat={lat}, lon={lon}, bearing={bearing}\n"
    )


def _build_statistics_context(transcript: str, handicap: int) -> str:
    """Build statistics context block for the prompt."""
    try:
        golf_stats = get_golf_statistics()
        stats = golf_stats.get_stats(handicap)
        if not stats:
            return ""
        
        # Parse the transcript to extract distance if mentioned
        intent = parse_intent(transcript, handicap)
        distance = intent.distance_yards
        
        context_parts = [
            f"Player Profile: {stats.category} golfer (handicap {handicap})",
        ]
        
        # Show validation warning if present
        if intent.validation_warning:
            context_parts.append(f"Note: {intent.validation_warning}")
        
        # Add distance-specific context if distance is mentioned
        if distance:
            club_rec = stats.club_distances.get_club_for_distance(distance)
            proximity = stats.proximity_to_target.get_expected_proximity(distance)
            gir_pct = stats.greens_in_regulation.get_gir_percentage(distance)
            
            context_parts.extend([
                f"Recommended club for {distance}y: {club_rec}",
                f"Expected proximity from {distance}y: {proximity} feet",
                f"Greens-in-regulation rate from {distance}y: {gir_pct}%",
            ])
        
        # Add key performance indicators
        context_parts.extend([
            f"Overall GIR: {stats.greens_in_regulation.overall}%",
            f"Fairways hit: {stats.fairways_hit}%",
            f"Scrambling: {stats.short_game.scrambling_percentage}%",
            f"3-putt rate: {stats.putting.three_putts_per_round:.1f}/round",
        ])
        
        # Add club distances for reference
        key_clubs = [
            ("driver", stats.club_distances.driver),
            ("7-iron", stats.club_distances.seven_iron),
            ("pitching wedge", stats.club_distances.pitching_wedge),
        ]
        
        club_distances = ", ".join([f"{club}: {dist}y" for club, dist in key_clubs])
        context_parts.append(f"Typical distances: {club_distances}")
        
        return "Performance Data:\n" + "\n".join(f"- {part}" for part in context_parts) + "\n\n"
        
    except Exception:
        # Fail gracefully if statistics can't be loaded
        return f"Handicap {handicap} player\n\n"


def ask_openai(prompt: str, model: Optional[str] = None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    model_to_use = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model_to_use,
        messages=[
            {"role": "system", "content": "You are a witty golf caddie."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=180,
    )
    text = resp.choices[0].message.content or ""
    meta = {
        "id": getattr(resp, "id", None),
        "created": getattr(resp, "created", None),
        "model": getattr(resp, "model", None),
        "usage": {
            "prompt_tokens": getattr(getattr(resp, "usage", None), "prompt_tokens", None),
            "completion_tokens": getattr(getattr(resp, "usage", None), "completion_tokens", None),
            "total_tokens": getattr(getattr(resp, "usage", None), "total_tokens", None),
        },
    }
    return text, meta


