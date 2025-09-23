from unittest.mock import patch, MagicMock
from golfcaddie.parser import parse_intent, _extract_club_mention, _extract_handicap_mention, _validate_distance_club_combination


def test_parse_distance_and_lie_and_hazards():
    p = parse_intent("I'm 150 yards out in the rough, water left")
    assert p.distance_yards == 150
    assert p.lie == "rough"
    assert "water" in p.hazards


def test_parse_handles_bunker_sand():
    p = parse_intent("about 95y from the bunker")
    assert p.distance_yards == 95
    assert p.lie == "sand"


def test_extract_club_mention():
    # Test various club mentions
    assert _extract_club_mention("i hit my driver") == "driver"
    assert _extract_club_mention("should i use a 7 iron") == "7-iron"
    assert _extract_club_mention("hit a 3 wood") == "3-wood"
    assert _extract_club_mention("use my pitching wedge") == "pitching-wedge"
    assert _extract_club_mention("sand wedge") == "sand-wedge"
    assert _extract_club_mention("lob wedge") == "lob-wedge"
    assert _extract_club_mention("my pw") == "pitching-wedge"
    assert _extract_club_mention("use putter") == "putter"
    assert _extract_club_mention("no club mentioned") is None


def test_parse_intent_with_club_mention():
    p = parse_intent("I'm 150 yards out with my 7 iron")
    assert p.distance_yards == 150
    assert p.club_mentioned == "7-iron"
    assert p.lie == "fairway"


def test_parse_intent_with_handicap_validation():
    # Mock the statistics module to test validation
    with patch('golfcaddie.parser.get_golf_statistics') as mock_stats:
        mock_golf_stats = MagicMock()
        mock_golf_stats.validate_distance_claim.return_value = (False, "Unusually long")
        mock_stats.return_value = mock_golf_stats
        
        p = parse_intent("I hit my 7 iron 200 yards", handicap=15)
        assert p.distance_yards == 200
        assert p.club_mentioned == "7-iron"
        assert p.validation_warning == "Unusually long"


def test_validate_distance_club_combination():
    # Test with mocked statistics
    with patch('golfcaddie.parser.get_golf_statistics') as mock_stats:
        mock_golf_stats = MagicMock()
        mock_golf_stats.validate_distance_claim.return_value = (True, "Realistic")
        mock_stats.return_value = mock_golf_stats
        
        result = _validate_distance_club_combination(10, "7-iron", 140)
        assert result is None  # No warning for valid combination
        
        mock_golf_stats.validate_distance_claim.return_value = (False, "Too long")
        result = _validate_distance_club_combination(15, "7-iron", 200)
        assert result == "Too long"


def test_parse_intent_graceful_failure():
    # Test that parser works even if statistics module fails
    with patch('golfcaddie.parser.get_golf_statistics', side_effect=Exception("No stats")):
        p = parse_intent("I hit my 7 iron 150 yards", handicap=10)
        assert p.distance_yards == 150
        assert p.club_mentioned == "7-iron"
        assert p.validation_warning is None  # Should not crash


def test_extract_handicap_mention():
    # Test various handicap mentions
    assert _extract_handicap_mention("i'm a 15 handicap") == 15
    assert _extract_handicap_mention("my handicap is 8") == 8
    assert _extract_handicap_mention("5 handicap player here") == 5
    assert _extract_handicap_mention("handicap 12") == 12
    assert _extract_handicap_mention("i play to a 7") == 7
    assert _extract_handicap_mention("i play to 10") == 10
    assert _extract_handicap_mention("i'm a 20") == 20
    assert _extract_handicap_mention("scratch golfer") == 0
    assert _extract_handicap_mention("scratch player") == 0
    assert _extract_handicap_mention("no handicap mentioned") is None
    
    # Test edge cases
    assert _extract_handicap_mention("i'm a 35 handicap") == 30  # Clamped to max
    assert _extract_handicap_mention("i'm a -2 handicap") == 0   # Clamped to min


def test_parse_intent_with_handicap_extraction():
    p = parse_intent("I'm a 12 handicap, 150 yards out")
    assert p.distance_yards == 150
    assert p.handicap_mentioned == 12
    assert p.lie == "fairway"


def test_parse_intent_handicap_priority():
    # Test that mentioned handicap takes priority over provided handicap
    with patch('golfcaddie.parser.get_golf_statistics') as mock_stats:
        mock_golf_stats = MagicMock()
        mock_golf_stats.validate_distance_claim.return_value = (True, "Realistic")
        mock_stats.return_value = mock_golf_stats
        
        p = parse_intent("I'm a 5 handicap with my 7 iron at 150 yards", handicap=15)
        assert p.handicap_mentioned == 5
        # Should validate using the mentioned handicap (5), not the provided one (15)
        mock_golf_stats.validate_distance_claim.assert_called_with(5, "7-iron", 150)


def test_parse_intent_no_handicap_mentioned():
    # Test fallback to provided handicap when none mentioned
    with patch('golfcaddie.parser.get_golf_statistics') as mock_stats:
        mock_golf_stats = MagicMock()
        mock_golf_stats.validate_distance_claim.return_value = (True, "Realistic")
        mock_stats.return_value = mock_golf_stats
        
        p = parse_intent("150 yards with my 7 iron", handicap=10)
        assert p.handicap_mentioned is None
        # Should validate using the provided handicap
        mock_golf_stats.validate_distance_claim.assert_called_with(10, "7-iron", 150)

