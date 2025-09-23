"""Tests for golf statistics module."""

import pytest
from unittest.mock import patch, mock_open
import json

from golfcaddie.statistics import (
    GolfStatistics, 
    HandicapStats, 
    ClubDistances, 
    ProximityData,
    GreensInRegulation,
    ShortGame,
    PuttingStats,
    get_golf_statistics
)


@pytest.fixture
def sample_stats_data():
    """Sample golf statistics data for testing."""
    return {
        "metadata": {
            "title": "Test Golf Statistics",
            "units": {"distance": "yards", "proximity": "feet"}
        },
        "handicap_statistics": {
            "0": {
                "handicap": 0,
                "category": "Scratch",
                "club_distances": {
                    "driver": 285,
                    "3_wood": 270,
                    "5_wood": 250,
                    "3_iron": 230,
                    "4_iron": 220,
                    "5_iron": 200,
                    "6_iron": 185,
                    "7_iron": 170,
                    "8_iron": 155,
                    "9_iron": 140,
                    "pitching_wedge": 125,
                    "sand_wedge": 110,
                    "lob_wedge": 95
                },
                "proximity_to_target": {
                    "50_yards": 8,
                    "75_yards": 12,
                    "100_yards": 18,
                    "125_yards": 25,
                    "150_yards": 35,
                    "175_yards": 45,
                    "200_yards": 60
                },
                "greens_in_regulation": {
                    "overall": 72,
                    "100_125_yards": 85,
                    "125_150_yards": 78,
                    "150_175_yards": 65,
                    "175_200_yards": 52,
                    "200_plus_yards": 35
                },
                "short_game": {
                    "sand_save_percentage": 65,
                    "up_and_down_0_25_yards": 75,
                    "up_and_down_25_50_yards": 68,
                    "scrambling_percentage": 70
                },
                "putting": {
                    "putts_per_round": 28.5,
                    "one_putts_per_round": 5.2,
                    "three_putts_per_round": 1.3,
                    "make_percentage_3_feet": 98,
                    "make_percentage_6_feet": 85,
                    "make_percentage_10_feet": 55,
                    "make_percentage_15_feet": 35,
                    "make_percentage_20_feet": 22
                },
                "course_management": {
                    "fairways_hit": 68,
                    "penalty_strokes_per_round": 1.2,
                    "average_score": 72
                }
            },
            "15": {
                "handicap": 15,
                "category": "Mid Double Digit",
                "club_distances": {
                    "driver": 235,
                    "3_wood": 220,
                    "5_wood": 200,
                    "3_iron": 180,
                    "4_iron": 170,
                    "5_iron": 150,
                    "6_iron": 135,
                    "7_iron": 120,
                    "8_iron": 105,
                    "9_iron": 90,
                    "pitching_wedge": 75,
                    "sand_wedge": 60,
                    "lob_wedge": 45
                },
                "proximity_to_target": {
                    "50_yards": 40,
                    "75_yards": 54,
                    "100_yards": 74,
                    "125_yards": 92,
                    "150_yards": 116,
                    "175_yards": 145,
                    "200_yards": 175
                },
                "greens_in_regulation": {
                    "overall": 27,
                    "100_125_yards": 40,
                    "125_150_yards": 31,
                    "150_175_yards": 17,
                    "175_200_yards": 7,
                    "200_plus_yards": 2
                },
                "short_game": {
                    "sand_save_percentage": 17,
                    "up_and_down_0_25_yards": 27,
                    "up_and_down_25_50_yards": 20,
                    "scrambling_percentage": 22
                },
                "putting": {
                    "putts_per_round": 40.2,
                    "one_putts_per_round": 0.6,
                    "three_putts_per_round": 5.7,
                    "make_percentage_3_feet": 76,
                    "make_percentage_6_feet": 36,
                    "make_percentage_10_feet": 10,
                    "make_percentage_15_feet": 3,
                    "make_percentage_20_feet": 1
                },
                "course_management": {
                    "fairways_hit": 23,
                    "penalty_strokes_per_round": 5.6,
                    "average_score": 87
                }
            }
        }
    }


class TestClubDistances:
    def test_from_dict(self):
        data = {
            "driver": 285,
            "3_wood": 270,
            "7_iron": 170,
            "pitching_wedge": 125,
            "5_wood": 250,
            "3_iron": 230,
            "4_iron": 220,
            "5_iron": 200,
            "6_iron": 185,
            "8_iron": 155,
            "9_iron": 140,
            "sand_wedge": 110,
            "lob_wedge": 95
        }
        
        distances = ClubDistances.from_dict(data)
        assert distances.driver == 285
        assert distances.seven_iron == 170
        assert distances.pitching_wedge == 125

    def test_get_club_for_distance(self):
        distances = ClubDistances(
            driver=285, three_wood=270, five_wood=250,
            three_iron=230, four_iron=220, five_iron=200,
            six_iron=185, seven_iron=170, eight_iron=155,
            nine_iron=140, pitching_wedge=125, sand_wedge=110, lob_wedge=95
        )
        
        assert distances.get_club_for_distance(170) == "7-iron"
        assert distances.get_club_for_distance(125) == "pitching-wedge"
        assert distances.get_club_for_distance(285) == "driver"
        assert distances.get_club_for_distance(100) == "sand-wedge"


class TestProximityData:
    def test_from_dict(self):
        data = {
            "50_yards": 8,
            "75_yards": 12,
            "100_yards": 18,
            "125_yards": 25,
            "150_yards": 35,
            "175_yards": 45,
            "200_yards": 60
        }
        
        proximity = ProximityData.from_dict(data)
        assert proximity.yards_50 == 8
        assert proximity.yards_150 == 35

    def test_get_expected_proximity(self):
        proximity = ProximityData(
            yards_50=8, yards_75=12, yards_100=18,
            yards_125=25, yards_150=35, yards_175=45, yards_200=60
        )
        
        assert proximity.get_expected_proximity(50) == 8
        assert proximity.get_expected_proximity(100) == 18
        assert proximity.get_expected_proximity(175) == 45
        assert proximity.get_expected_proximity(250) == 60  # Above 200


class TestGreensInRegulation:
    def test_get_gir_percentage(self):
        gir = GreensInRegulation(
            overall=72, yards_100_125=85, yards_125_150=78,
            yards_150_175=65, yards_175_200=52, yards_200_plus=35
        )
        
        assert gir.get_gir_percentage(120) == 85
        assert gir.get_gir_percentage(140) == 78
        assert gir.get_gir_percentage(165) == 65
        assert gir.get_gir_percentage(190) == 52
        assert gir.get_gir_percentage(250) == 35


class TestPuttingStats:
    def test_get_make_percentage(self):
        putting = PuttingStats(
            putts_per_round=28.5, one_putts_per_round=5.2, three_putts_per_round=1.3,
            make_percentage_3_feet=98, make_percentage_6_feet=85,
            make_percentage_10_feet=55, make_percentage_15_feet=35,
            make_percentage_20_feet=22
        )
        
        assert putting.get_make_percentage(3) == 98
        assert putting.get_make_percentage(6) == 85
        assert putting.get_make_percentage(10) == 55
        assert putting.get_make_percentage(25) == 22  # Above 15


class TestGolfStatistics:
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_load_statistics(self, mock_exists, mock_file, sample_stats_data):
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_stats_data)
        
        stats = GolfStatistics("test_file.json")
        
        # Test that data was loaded correctly
        scratch_stats = stats.get_stats(0)
        assert scratch_stats is not None
        assert scratch_stats.handicap == 0
        assert scratch_stats.category == "Scratch"
        assert scratch_stats.club_distances.driver == 285

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_get_expected_distance(self, mock_exists, mock_file, sample_stats_data):
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_stats_data)
        
        stats = GolfStatistics("test_file.json")
        
        # Test distance lookup
        assert stats.get_expected_distance(0, "driver") == 285
        assert stats.get_expected_distance(0, "7-iron") == 170
        assert stats.get_expected_distance(15, "driver") == 235
        assert stats.get_expected_distance(15, "7-iron") == 120

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_get_club_recommendation(self, mock_exists, mock_file, sample_stats_data):
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_stats_data)
        
        stats = GolfStatistics("test_file.json")
        
        # Test club recommendations
        assert stats.get_club_recommendation(0, 170) == "7-iron"
        assert stats.get_club_recommendation(15, 120) == "7-iron"
        assert stats.get_club_recommendation(0, 285) == "driver"

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_validate_distance_claim(self, mock_exists, mock_file, sample_stats_data):
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_stats_data)
        
        stats = GolfStatistics("test_file.json")
        
        # Test realistic distance claims
        is_valid, reason = stats.validate_distance_claim(0, "7-iron", 170)
        assert is_valid
        assert reason == "Realistic"
        
        # Test unrealistic distance claims
        is_valid, reason = stats.validate_distance_claim(15, "7-iron", 200)
        assert not is_valid
        assert "Unusually long" in reason

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_get_performance_context(self, mock_exists, mock_file, sample_stats_data):
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_stats_data)
        
        stats = GolfStatistics("test_file.json")
        
        context = stats.get_performance_context(0, 150)
        assert "Scratch" in context
        assert "150y" in context
        assert "35ft" in context  # proximity
        assert "65%" in context  # GIR rate

    def test_handicap_clamping(self):
        # Test that handicaps are clamped to valid range
        with patch("builtins.open", new_callable=mock_open), \
             patch("pathlib.Path.exists", return_value=True):
            
            mock_data = {"handicap_statistics": {"0": {}, "20": {}}}
            with patch("json.load", return_value=mock_data):
                stats = GolfStatistics("test_file.json")
                
                # These should be clamped to valid range
                assert stats.get_stats(-5) == stats.get_stats(0)
                assert stats.get_stats(25) == stats.get_stats(20)


class TestGlobalInstance:
    @patch("golfcaddie.statistics.GolfStatistics")
    def test_get_golf_statistics_singleton(self, mock_stats_class):
        # Reset the global instance
        import golfcaddie.statistics
        golfcaddie.statistics._golf_stats = None
        
        # First call should create instance
        stats1 = get_golf_statistics()
        mock_stats_class.assert_called_once()
        
        # Second call should return same instance
        mock_stats_class.reset_mock()
        stats2 = get_golf_statistics()
        mock_stats_class.assert_not_called()
        
        assert stats1 is stats2