"""Tests for psychrometric calculations."""

from custom_components.kellerlueftung.calculations import absolute_humidity_g_m3, dew_point_c


def test_absolute_humidity_reference_point() -> None:
    """20 °C and 50 % RH is approximately 8.64 g/m³."""
    assert absolute_humidity_g_m3(20.0, 50.0) == pytest.approx(8.64, abs=0.05)


def test_dew_point_reference_point() -> None:
    """20 °C and 50 % RH has a dew point of approximately 9.3 °C."""
    assert dew_point_c(20.0, 50.0) == pytest.approx(9.26, abs=0.1)


import pytest
