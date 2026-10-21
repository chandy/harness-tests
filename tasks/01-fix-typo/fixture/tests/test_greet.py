from src.greet import greet


def test_greet_basic():
    assert greet("Ada") == "Hello, Ada!"


def test_greet_empty():
    assert greet("") == "Hello, !"
