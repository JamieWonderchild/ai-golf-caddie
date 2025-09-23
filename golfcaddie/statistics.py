"""Golf statistics module for handicap-specific performance data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any
from pathlib import Path


@dataclass
class ClubDistances:
    """Expected distances for each club by handicap."""
    driver: int
    three_wood: int
    five_wood: int
    three_iron: int
    four_iron: int
    five_iron: int
    six_iron: int
    seven_iron: int
    eight_iron: int
    nine_iron: int
    pitching_wedge: int
    sand_wedge: int
    lob_wedge: int

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'ClubDistances':
        """Create ClubDistances from dictionary with key mapping."""
        return cls(
            driver=data["driver"],
            three_wood=data["3_wood"],
            five_wood=data["5_wood"],
            three_iron=data["3_iron"],
            four_iron=data["4_iron"],
            five_iron=data["5_iron"],
            six_iron=data["6_iron"],
            seven_iron=data["7_iron"],
            eight_iron=data["8_iron"],
            nine_iron=data["9_iron"],
            pitching_wedge=data["pitching_wedge"],
            sand_wedge=data["sand_wedge"],
            lob_wedge=data["lob_wedge"],
        )

    def get_club_for_distance(self, target_distance: int) -> str:
        """Find the most appropriate club for a given distance."""
        clubs = [
            ("lob_wedge", self.lob_wedge),
            ("sand_wedge", self.sand_wedge),
            ("pitching_wedge", self.pitching_wedge),
            ("9_iron", self.nine_iron),
            ("8_iron", self.eight_iron),
            ("7_iron", self.seven_iron),
            ("6_iron", self.six_iron),
            ("5_iron", self.five_iron),
            ("4_iron", self.four_iron),
            ("3_iron", self.three_iron),
            ("5_wood", self.five_wood),
            ("3_wood", self.three_wood),
            ("driver", self.driver),
        ]
        
        # Find the club with distance closest to but not significantly under target
        best_club = "7_iron"  # Default fallback
        best_diff = float('inf')
        
        for club_name, club_distance in clubs:
            # Prefer clubs that can reach the distance, but allow some under-club tolerance
            diff = abs(target_distance - club_distance)
            if club_distance >= target_distance * 0.9:  # Allow 10% under-club tolerance
                if diff < best_diff:
                    best_diff = diff
                    best_club = club_name
        
        return best_club.replace("_", "-")


@dataclass
class ProximityData:
    """Proximity to target data by distance."""
    yards_50: int
    yards_75: int
    yards_100: int
    yards_125: int
    yards_150: int
    yards_175: int
    yards_200: int

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'ProximityData':
        """Create ProximityData from dictionary."""
        return cls(
            yards_50=data["50_yards"],
            yards_75=data["75_yards"],
            yards_100=data["100_yards"],
            yards_125=data["125_yards"],
            yards_150=data["150_yards"],
            yards_175=data["175_yards"],
            yards_200=data["200_yards"],
        )

    def get_expected_proximity(self, distance: int) -> int:
        """Get expected proximity for a given approach distance."""
        if distance <= 50:
            return self.yards_50
        elif distance <= 75:
            return self.yards_75
        elif distance <= 100:
            return self.yards_100
        elif distance <= 125:
            return self.yards_125
        elif distance <= 150:
            return self.yards_150
        elif distance <= 175:
            return self.yards_175
        else:
            return self.yards_200


@dataclass
class GreensInRegulation:
    """Greens in regulation percentages by distance."""
    overall: int
    yards_100_125: int
    yards_125_150: int
    yards_150_175: int
    yards_175_200: int
    yards_200_plus: int

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'GreensInRegulation':
        """Create GreensInRegulation from dictionary."""
        return cls(
            overall=data["overall"],
            yards_100_125=data["100_125_yards"],
            yards_125_150=data["125_150_yards"],
            yards_150_175=data["150_175_yards"],
            yards_175_200=data["175_200_yards"],
            yards_200_plus=data["200_plus_yards"],
        )

    def get_gir_percentage(self, distance: int) -> int:
        """Get expected GIR percentage for a given distance."""
        if distance <= 125:
            return self.yards_100_125
        elif distance <= 150:
            return self.yards_125_150
        elif distance <= 175:
            return self.yards_150_175
        elif distance <= 200:
            return self.yards_175_200
        else:
            return self.yards_200_plus


@dataclass
class ShortGame:
    """Short game statistics."""
    sand_save_percentage: int
    up_and_down_0_25_yards: int
    up_and_down_25_50_yards: int
    scrambling_percentage: int

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'ShortGame':
        """Create ShortGame from dictionary."""
        return cls(
            sand_save_percentage=data["sand_save_percentage"],
            up_and_down_0_25_yards=data["up_and_down_0_25_yards"],
            up_and_down_25_50_yards=data["up_and_down_25_50_yards"],
            scrambling_percentage=data["scrambling_percentage"],
        )


@dataclass
class PuttingStats:
    """Putting statistics."""
    putts_per_round: float
    one_putts_per_round: float
    three_putts_per_round: float
    make_percentage_3_feet: int
    make_percentage_6_feet: int
    make_percentage_10_feet: int
    make_percentage_15_feet: int
    make_percentage_20_feet: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PuttingStats':
        """Create PuttingStats from dictionary."""
        return cls(
            putts_per_round=data["putts_per_round"],
            one_putts_per_round=data["one_putts_per_round"],
            three_putts_per_round=data["three_putts_per_round"],
            make_percentage_3_feet=data["make_percentage_3_feet"],
            make_percentage_6_feet=data["make_percentage_6_feet"],
            make_percentage_10_feet=data["make_percentage_10_feet"],
            make_percentage_15_feet=data["make_percentage_15_feet"],
            make_percentage_20_feet=data["make_percentage_20_feet"],
        )

    def get_make_percentage(self, distance_feet: int) -> int:
        """Get expected make percentage for a given putt distance."""
        if distance_feet <= 3:
            return self.make_percentage_3_feet
        elif distance_feet <= 6:
            return self.make_percentage_6_feet
        elif distance_feet <= 10:
            return self.make_percentage_10_feet
        elif distance_feet <= 15:
            return self.make_percentage_15_feet
        else:
            return self.make_percentage_20_feet


@dataclass
class HandicapStats:
    """Complete statistics for a specific handicap level."""
    handicap: int
    category: str
    club_distances: ClubDistances
    proximity_to_target: ProximityData
    greens_in_regulation: GreensInRegulation
    short_game: ShortGame
    putting: PuttingStats
    fairways_hit: int
    penalty_strokes_per_round: float
    average_score: int

    @classmethod
    def from_dict(cls, handicap: int, data: Dict[str, Any]) -> 'HandicapStats':
        """Create HandicapStats from dictionary."""
        return cls(
            handicap=handicap,
            category=data["category"],
            club_distances=ClubDistances.from_dict(data["club_distances"]),
            proximity_to_target=ProximityData.from_dict(data["proximity_to_target"]),
            greens_in_regulation=GreensInRegulation.from_dict(data["greens_in_regulation"]),
            short_game=ShortGame.from_dict(data["short_game"]),
            putting=PuttingStats.from_dict(data["putting"]),
            fairways_hit=data["course_management"]["fairways_hit"],
            penalty_strokes_per_round=data["course_management"]["penalty_strokes_per_round"],
            average_score=data["course_management"]["average_score"],
        )


class GolfStatistics:
    """Golf statistics database for handicap-specific performance data."""
    
    def __init__(self, stats_file: Optional[str] = None):
        """Initialize with statistics data file."""
        if stats_file is None:
            # Default to the JSON file in the same directory as this project
            current_dir = Path(__file__).parent.parent
            stats_file = current_dir / "golf_statistics_by_handicap.json"
        
        self.stats_file = Path(stats_file)
        self._stats_cache: Dict[int, HandicapStats] = {}
        self._load_statistics()
    
    def _load_statistics(self) -> None:
        """Load statistics from JSON file."""
        if not self.stats_file.exists():
            raise FileNotFoundError(f"Statistics file not found: {self.stats_file}")
        
        with open(self.stats_file, 'r') as f:
            data = json.load(f)
        
        handicap_data = data["handicap_statistics"]
        for handicap_str, stats_dict in handicap_data.items():
            handicap = int(handicap_str)
            self._stats_cache[handicap] = HandicapStats.from_dict(handicap, stats_dict)
    
    def get_stats(self, handicap: int) -> Optional[HandicapStats]:
        """Get statistics for a specific handicap (0-20)."""
        # Clamp handicap to valid range
        handicap = max(0, min(20, handicap))
        return self._stats_cache.get(handicap)
    
    def get_expected_distance(self, handicap: int, club: str) -> Optional[int]:
        """Get expected distance for a club and handicap."""
        stats = self.get_stats(handicap)
        if not stats:
            return None
        
        club_attr = club.lower().replace("-", "_").replace(" ", "_")
        return getattr(stats.club_distances, club_attr, None)
    
    def get_club_recommendation(self, handicap: int, target_distance: int) -> Optional[str]:
        """Get club recommendation for target distance and handicap."""
        stats = self.get_stats(handicap)
        if not stats:
            return None
        
        return stats.club_distances.get_club_for_distance(target_distance)
    
    def get_performance_context(self, handicap: int, distance: int) -> str:
        """Get performance context string for LLM prompts."""
        stats = self.get_stats(handicap)
        if not stats:
            return f"Handicap {handicap} player"
        
        club_rec = stats.club_distances.get_club_for_distance(distance)
        proximity = stats.proximity_to_target.get_expected_proximity(distance)
        gir_pct = stats.greens_in_regulation.get_gir_percentage(distance)
        
        context_parts = [
            f"Handicap {handicap} ({stats.category})",
            f"Typical {club_rec} for {distance}y",
            f"Expected proximity: {proximity}ft",
            f"GIR rate: {gir_pct}%",
        ]
        
        return " | ".join(context_parts)
    
    def validate_distance_claim(self, handicap: int, club: str, claimed_distance: int) -> tuple[bool, str]:
        """Validate if a claimed distance is realistic for handicap/club combination."""
        expected = self.get_expected_distance(handicap, club)
        if expected is None:
            return True, "Unknown club"
        
        # Allow ±20% variance from expected distance
        lower_bound = expected * 0.8
        upper_bound = expected * 1.2
        
        if lower_bound <= claimed_distance <= upper_bound:
            return True, "Realistic"
        elif claimed_distance < lower_bound:
            return False, f"Unusually short (expected ~{expected}y)"
        else:
            return False, f"Unusually long (expected ~{expected}y)"


# Global instance for easy access
_golf_stats: Optional[GolfStatistics] = None


def get_golf_statistics() -> GolfStatistics:
    """Get the global golf statistics instance."""
    global _golf_stats
    if _golf_stats is None:
        _golf_stats = GolfStatistics()
    return _golf_stats