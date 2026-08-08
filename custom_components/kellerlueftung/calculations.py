"""Psychrometric calculations used by Kellerlüftung."""

from __future__ import annotations

import math


def saturation_vapor_pressure_hpa(temperature_c: float) -> float:
    """Return saturation vapor pressure in hPa using the Magnus equation."""
    a = 17.62 if temperature_c >= 0 else 22.46
    b = 243.12 if temperature_c >= 0 else 272.62
    return 6.112 * math.exp((a * temperature_c) / (b + temperature_c))


def absolute_humidity_g_m3(temperature_c: float, relative_humidity: float) -> float:
    """Return absolute humidity in g/m³."""
    vapor_pressure = saturation_vapor_pressure_hpa(temperature_c) * relative_humidity / 100.0
    return 216.7 * vapor_pressure / (273.15 + temperature_c)


def dew_point_c(temperature_c: float, relative_humidity: float) -> float:
    """Return dew point in °C using the Magnus formula."""
    rh = min(max(relative_humidity, 0.1), 100.0)
    a = 17.62 if temperature_c >= 0 else 22.46
    b = 243.12 if temperature_c >= 0 else 272.62
    gamma = math.log(rh / 100.0) + (a * temperature_c) / (b + temperature_c)
    return (b * gamma) / (a - gamma)
