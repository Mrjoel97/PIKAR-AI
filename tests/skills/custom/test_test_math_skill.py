
import pytest
from app.skills.custom.test_math_skill import calculator_func

def test_calculator():
    assert calculator_func(5, 10) == 15
    assert calculator_func(-1, 1) == 0
