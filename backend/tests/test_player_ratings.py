from app.modules.players.ratings import position_rating_grade, rating_grade


def test_rating_grade_boundaries() -> None:
    assert rating_grade(None) is None
    assert rating_grade(49) == "D"
    assert rating_grade(50) == "C"
    assert rating_grade(64) == "C"
    assert rating_grade(65) == "B"
    assert rating_grade(74) == "B"
    assert rating_grade(75) == "A"
    assert rating_grade(84) == "A"
    assert rating_grade(85) == "A+"


def test_position_rating_uses_modifier_without_exposing_number() -> None:
    assert position_rating_grade("84+1") == "A+"
    assert position_rating_grade("85-1") == "A"
    assert position_rating_grade(None) is None
