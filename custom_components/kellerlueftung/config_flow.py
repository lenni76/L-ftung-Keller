"""Config flow for Kellerlüftung."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_DRYER_1,
    CONF_DRYER_2,
    CONF_FAN_ENTITY,
    CONF_INDOOR_HUMIDITY,
    CONF_INDOOR_TEMPERATURE,
    CONF_OUTDOOR_HUMIDITY,
    CONF_OUTDOOR_TEMPERATURE,
    DEFAULTS,
    DOMAIN,
    NAME,
    OPT_DELTA_HIGH,
    OPT_DELTA_LOW,
    OPT_DELTA_MEDIUM,
    OPT_DRYER_BONUS,
    OPT_DRYER_POWER_THRESHOLD,
    OPT_HUMIDITY_HIGH,
    OPT_HUMIDITY_MEDIUM,
    OPT_MAX_RUNTIME,
    OPT_MIN_HUMIDITY,
    OPT_MIN_PAUSE,
    OPT_MIN_RUNTIME,
    OPT_STOP_DELTA,
)

SENSOR_SELECTOR = EntitySelector(EntitySelectorConfig(domain=["sensor"]))
FAN_SELECTOR = EntitySelector(EntitySelectorConfig(domain=["fan", "switch"]))
DRYER_SELECTOR = EntitySelector(EntitySelectorConfig(domain=["binary_sensor", "sensor"]))


def _config_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    schema: dict[Any, Any] = {
        vol.Required(CONF_INDOOR_TEMPERATURE, default=defaults.get(CONF_INDOOR_TEMPERATURE)): SENSOR_SELECTOR,
        vol.Required(CONF_INDOOR_HUMIDITY, default=defaults.get(CONF_INDOOR_HUMIDITY)): SENSOR_SELECTOR,
        vol.Required(CONF_OUTDOOR_TEMPERATURE, default=defaults.get(CONF_OUTDOOR_TEMPERATURE)): SENSOR_SELECTOR,
        vol.Required(CONF_OUTDOOR_HUMIDITY, default=defaults.get(CONF_OUTDOOR_HUMIDITY)): SENSOR_SELECTOR,
        vol.Required(CONF_FAN_ENTITY, default=defaults.get(CONF_FAN_ENTITY)): FAN_SELECTOR,
    }
    if defaults.get(CONF_DRYER_1):
        schema[vol.Optional(CONF_DRYER_1, default=defaults[CONF_DRYER_1])] = DRYER_SELECTOR
    else:
        schema[vol.Optional(CONF_DRYER_1)] = DRYER_SELECTOR
    if defaults.get(CONF_DRYER_2):
        schema[vol.Optional(CONF_DRYER_2, default=defaults[CONF_DRYER_2])] = DRYER_SELECTOR
    else:
        schema[vol.Optional(CONF_DRYER_2)] = DRYER_SELECTOR
    return vol.Schema(schema)


def _number(minimum: float, maximum: float, step: float, unit: str | None = None) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=unit,
        )
    )


def _options_schema(current: dict[str, Any]) -> vol.Schema:
    values = {**DEFAULTS, **current}
    return vol.Schema(
        {
            vol.Required(OPT_MIN_HUMIDITY, default=values[OPT_MIN_HUMIDITY]): _number(30, 90, 1, "%"),
            vol.Required(OPT_HUMIDITY_MEDIUM, default=values[OPT_HUMIDITY_MEDIUM]): _number(40, 95, 1, "%"),
            vol.Required(OPT_HUMIDITY_HIGH, default=values[OPT_HUMIDITY_HIGH]): _number(50, 100, 1, "%"),
            vol.Required(OPT_DELTA_LOW, default=values[OPT_DELTA_LOW]): _number(0.1, 5.0, 0.1, "g/m³"),
            vol.Required(OPT_DELTA_MEDIUM, default=values[OPT_DELTA_MEDIUM]): _number(0.1, 5.0, 0.1, "g/m³"),
            vol.Required(OPT_DELTA_HIGH, default=values[OPT_DELTA_HIGH]): _number(0.1, 5.0, 0.1, "g/m³"),
            vol.Required(OPT_STOP_DELTA, default=values[OPT_STOP_DELTA]): _number(0.0, 3.0, 0.1, "g/m³"),
            vol.Required(OPT_DRYER_BONUS, default=values[OPT_DRYER_BONUS]): _number(0.0, 2.0, 0.1, "g/m³"),
            vol.Required(OPT_DRYER_POWER_THRESHOLD, default=values[OPT_DRYER_POWER_THRESHOLD]): _number(0, 5000, 1, "W"),
            vol.Required(OPT_MIN_RUNTIME, default=values[OPT_MIN_RUNTIME]): _number(0, 180, 1, "min"),
            vol.Required(OPT_MIN_PAUSE, default=values[OPT_MIN_PAUSE]): _number(0, 180, 1, "min"),
            vol.Required(OPT_MAX_RUNTIME, default=values[OPT_MAX_RUNTIME]): _number(0, 1440, 1, "min"),
        }
    )


def _validate_options(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not (data[OPT_MIN_HUMIDITY] <= data[OPT_HUMIDITY_MEDIUM] <= data[OPT_HUMIDITY_HIGH]):
        errors["base"] = "humidity_order"
    elif data[OPT_STOP_DELTA] >= min(data[OPT_DELTA_LOW], data[OPT_DELTA_MEDIUM], data[OPT_DELTA_HIGH]):
        errors["base"] = "stop_delta_too_high"
    return errors


class KellerlueftungConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kellerlüftung."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial setup."""
        if user_input is not None:
            self._async_abort_entries_match({})
            return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_config_schema())

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Allow changing selected entities."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            return self.async_update_and_abort(entry, data=user_input)

        return self.async_show_form(step_id="reconfigure", data_schema=_config_schema(dict(entry.data)))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return options flow."""
        return KellerlueftungOptionsFlow()


class KellerlueftungOptionsFlow(config_entries.OptionsFlow):
    """Handle Kellerlüftung options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_options(user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(user_input or dict(self.config_entry.options)),
            errors=errors,
        )
