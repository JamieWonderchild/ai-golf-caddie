import pytest
from unittest.mock import patch, MagicMock

from golfcaddie.binning import (
    bin_distance_yards, 
    bin_wind_components, 
    compute_context_bins,
    bin_handicap,
    get_performance_expectation
)


@pytest.mark.parametrize(
    "distance,bin_size,expected",
    [
        (0, 10, 0),
        (9, 10, 0),
        (10, 10, 10),
        (19, 10, 10),
        (20, 10, 20),
        (153, 10, 150),
    ],
)
def test_bin_distance(distance, bin_size, expected):
    assert bin_distance_yards(distance, bin_size) == expected


def test_bin_distance_invalid():
    with pytest.raises(ValueError):
        bin_distance_yards(100, 0)


def test_bin_wind_components_labels():
    assert bin_wind_components(0.0, 0.0) == "head_0|cross_00"
    # positive crosswind pushes ball right-to-left
    assert bin_wind_components(3.0, 1.0).startswith("head_2|cross_0R")
    assert bin_wind_components(-5.0, -3.9).startswith("tail_4|cross_2L")


def test_compute_context_bins():
    bins = compute_context_bins(157, 3.2, -2.1, 10)
    assert bins.distance_bin == 150
    assert bins.wind_bin.startswith("head_2|cross_2L")


def test_bin_handicap():
    assert bin_handicap(0) == "scratch"
    assert bin_handicap(3) == "low_single"
    assert bin_handicap(8) == "high_single"
    assert bin_handicap(12) == "low_double"
    assert bin_handicap(18) == "high_double"
    assert bin_handicap(25) == "high_handicap"


def test_get_performance_expectation():
    # Mock statistics module
    with patch('golfcaddie.binning.get_golf_statistics') as mock_stats:
        mock_golf_stats = MagicMock()
        mock_stats_obj = MagicMock()
        mock_stats_obj.greens_in_regulation.get_gir_percentage.return_value = 60
        mock_stats_obj.proximity_to_target.get_expected_proximity.return_value = 25
        mock_golf_stats.get_stats.return_value = mock_stats_obj
        mock_stats.return_value = mock_golf_stats
        
        result = get_performance_expectation(150, 5)
        assert result == "high_gir_60pct_25ft"
        
        # Test medium GIR
        mock_stats_obj.greens_in_regulation.get_gir_percentage.return_value = 35
        result = get_performance_expectation(150, 10)
        assert result == "med_gir_35pct_25ft"
        
        # Test low GIR
        mock_stats_obj.greens_in_regulation.get_gir_percentage.return_value = 15
        result = get_performance_expectation(150, 18)
        assert result == "low_gir_15pct_25ft"


def test_get_performance_expectation_no_stats():
    # Test graceful failure when stats not available
    with patch('golfcaddie.binning.get_golf_statistics', side_effect=Exception("No stats")):
        result = get_performance_expectation(150, 10)
        assert result == "unknown"


def test_compute_context_bins_with_handicap():
    # Mock performance expectation
    with patch('golfcaddie.binning.get_performance_expectation', return_value="high_gir_60pct_25ft"):
        bins = compute_context_bins(157, 3.2, -2.1, handicap=5, bin_size=10)
        
        assert bins.distance_bin == 150
        assert bins.wind_bin.startswith("head_2|cross_2L")
        assert bins.handicap_bin == "low_single"
        assert bins.performance_expectation == "high_gir_60pct_25ft"


def test_compute_context_bins_no_handicap():
    bins = compute_context_bins(157, 3.2, -2.1, bin_size=10)
    
    assert bins.distance_bin == 150
    assert bins.wind_bin.startswith("head_2|cross_2L")
    assert bins.handicap_bin is None
    assert bins.performance_expectation is None

