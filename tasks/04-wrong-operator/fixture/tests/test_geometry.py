from src.geometry import area


def test_area_integers():
    assert area(3, 4) == 12


def test_area_floats():
    assert area(2.5, 2) == 5.0
