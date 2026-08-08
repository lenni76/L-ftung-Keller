"""Constants for the Kellerlüftung integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "kellerlueftung"
NAME = "Kellerlüftung"
VERSION = "1.0.0"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SELECT]

CONF_INDOOR_TEMPERATURE = "indoor_temperature"
CONF_INDOOR_HUMIDITY = "indoor_humidity"
CONF_OUTDOOR_TEMPERATURE = "outdoor_temperature"
CONF_OUTDOOR_HUMIDITY = "outdoor_humidity"
CONF_FAN_ENTITY = "fan_entity"
CONF_DRYER_1 = "dryer_1"
CONF_DRYER_2 = "dryer_2"

OPT_DRYER_POWER_THRESHOLD = "dryer_power_threshold"
OPT_MIN_HUMIDITY = "min_humidity"
OPT_HUMIDITY_MEDIUM = "humidity_medium"
OPT_HUMIDITY_HIGH = "humidity_high"
OPT_DELTA_LOW = "delta_low"
OPT_DELTA_MEDIUM = "delta_medium"
OPT_DELTA_HIGH = "delta_high"
OPT_STOP_DELTA = "stop_delta"
OPT_DRYER_BONUS = "dryer_bonus"
OPT_MIN_RUNTIME = "min_runtime"
OPT_MIN_PAUSE = "min_pause"
OPT_MAX_RUNTIME = "max_runtime"

DEFAULTS = {
    OPT_DRYER_POWER_THRESHOLD: 10.0,
    OPT_MIN_HUMIDITY: 60.0,
    OPT_HUMIDITY_MEDIUM: 65.0,
    OPT_HUMIDITY_HIGH: 75.0,
    OPT_DELTA_LOW: 1.5,
    OPT_DELTA_MEDIUM: 1.0,
    OPT_DELTA_HIGH: 0.5,
    OPT_STOP_DELTA: 0.4,
    OPT_DRYER_BONUS: 0.5,
    OPT_MIN_RUNTIME: 10,
    OPT_MIN_PAUSE: 10,
    OPT_MAX_RUNTIME: 0,
}

MODE_AUTOMATIC = "Automatik"
MODE_OFF = "Aus"
MODE_MANUAL_ON = "Manuell ein"
MODES = [MODE_AUTOMATIC, MODE_OFF, MODE_MANUAL_ON]

SIGNAL_UPDATE = f"{DOMAIN}_update"
