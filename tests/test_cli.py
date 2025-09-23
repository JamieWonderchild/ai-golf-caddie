import re
from click.testing import CliRunner

from golfcaddie.cli import cli


def test_cli_weather(monkeypatch):
    runner = CliRunner()

    # Stub weather to deterministic values
    monkeypatch.setattr(
        "golfcaddie.weather.get_wind",
        lambda lat, lon, b: type(
            "W",
            (),
            {
                "speed_ms": 4.0,
                "direction_deg": 270,
                "headwind_ms": 2.0,
                "crosswind_ms": -1.0,
                "summary": "9 mph, headwind, left-to-right",
            },
        )(),
    )

    res = runner.invoke(cli, ["weather", "40", "105", "0"])
    assert res.exit_code == 0, res.output
    assert "Headwind: 2.0 m/s" in res.output


def test_detect_intent_weather_patterns():
    """Test that weather intent detection patterns work correctly."""
    from golfcaddie.cli import _detect_intent
    
    # Test cases that should be detected as weather
    weather_queries = [
        "Can you tell me about the conditions",
        "Can you tell me a little bit about the conditions",
        "What are the current conditions",
        "Tell me about the weather",
        "What's the wind like",
        "How windy is it",
        "Check the conditions",
        "Conditions today",
        "Weather now",
        "What is the forecast",
    ]
    
    for query in weather_queries:
        intent = _detect_intent(query)
        assert intent == "weather", f"Failed to detect weather intent for: '{query}'"
    
    # Test cases that should be detected as shot
    shot_queries = [
        "What club should I use",
        "I'm 150 yards out",
        "Recommend a club",
        "Should I hit a 7 iron",
        "Which club for this shot",
    ]
    
    for query in shot_queries:
        intent = _detect_intent(query)
        assert intent == "shot", f"Incorrectly detected weather intent for: '{query}'"

