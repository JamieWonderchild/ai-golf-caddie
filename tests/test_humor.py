from golfcaddie.humor import HumorContext, generate_humor


def test_humor_low_ambition():
    ctx = HumorContext(
        handicap=10,
        distance_yards=140,
        lie="fairway",
        hazards=[],
        recommended_club="9i",
        shot_type="normal",
        aim_offset_yards=0,
        confidence=0.8,
    )
    msg = generate_humor(ctx)
    assert "Sensible" in msg and "Green light" in msg


def test_humor_high_ambition_with_hazards_and_offset():
    ctx = HumorContext(
        handicap=22,
        distance_yards=190,
        lie="rough",
        hazards=["water_left"],
        recommended_club="3w",
        shot_type="punch",
        aim_offset_yards=8,
        confidence=0.45,
        go_to_hint=None,
    )
    msg = generate_humor(ctx)
    assert "Ambitious" in msg
    assert "aim 8 yards right" in msg
    assert "water_left" in msg
    assert "percentages" in msg

