"""Control logic for Kellerlüftung."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .calculations import absolute_humidity_g_m3, dew_point_c
from .const import (
    CONF_DRYER_1,
    CONF_DRYER_2,
    CONF_FAN_ENTITY,
    CONF_INDOOR_HUMIDITY,
    CONF_INDOOR_TEMPERATURE,
    CONF_OUTDOOR_HUMIDITY,
    CONF_OUTDOOR_TEMPERATURE,
    DEFAULTS,
    MODE_AUTOMATIC,
    MODE_MANUAL_ON,
    MODE_OFF,
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
    SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VentilationSnapshot:
    """Current calculated ventilation state."""

    indoor_absolute_humidity: float | None = None
    outdoor_absolute_humidity: float | None = None
    humidity_delta: float | None = None
    indoor_dew_point: float | None = None
    outdoor_dew_point: float | None = None
    dryer_active: bool = False
    sensors_ok: bool = False
    ventilation_useful: bool = False
    status: str = "Initialisierung"
    reason: str = "Warte auf gültige Sensordaten"
    required_delta: float | None = None


class KellerlueftungController:
    """Evaluate sensor data and operate the configured fan."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.snapshot = VentilationSnapshot()
        self.mode = MODE_AUTOMATIC
        self._unsubs: list[Any] = []
        self._last_on: datetime | None = None
        self._last_off: datetime | None = None
        self._evaluation_pending = False

    @property
    def options(self) -> dict[str, Any]:
        """Return effective options with defaults."""
        return {**DEFAULTS, **self.entry.options}

    @property
    def fan_entity(self) -> str:
        """Return configured fan/switch entity."""
        return self.entry.data[CONF_FAN_ENTITY]

    async def async_start(self) -> None:
        """Start listeners and perform the initial evaluation."""
        entities = [
            self.entry.data[CONF_INDOOR_TEMPERATURE],
            self.entry.data[CONF_INDOOR_HUMIDITY],
            self.entry.data[CONF_OUTDOOR_TEMPERATURE],
            self.entry.data[CONF_OUTDOOR_HUMIDITY],
            self.fan_entity,
        ]
        for key in (CONF_DRYER_1, CONF_DRYER_2):
            entity_id = self.entry.data.get(key)
            if entity_id:
                entities.append(entity_id)

        self._unsubs.append(async_track_state_change_event(self.hass, entities, self._handle_state_change))
        self._unsubs.append(
            async_track_time_interval(self.hass, self._handle_interval, timedelta(minutes=1))
        )
        await self.async_evaluate()

    async def async_stop(self) -> None:
        """Stop listeners without changing the controlled device state."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @callback
    def _handle_state_change(self, _event: Any) -> None:
        self._schedule_evaluation()

    @callback
    def _handle_interval(self, _now: datetime) -> None:
        self._schedule_evaluation()

    @callback
    def _schedule_evaluation(self) -> None:
        if self._evaluation_pending:
            return
        self._evaluation_pending = True
        self.hass.async_create_task(self._async_scheduled_evaluate())

    async def _async_scheduled_evaluate(self) -> None:
        try:
            await self.async_evaluate()
        finally:
            self._evaluation_pending = False

    def _numeric_state(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        return value

    def _dryer_is_active(self, entity_id: str | None) -> bool:
        if not entity_id:
            return False
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return False
        if entity_id.startswith("binary_sensor."):
            return state.state == STATE_ON
        try:
            power = float(state.state)
        except (TypeError, ValueError):
            return False
        unit = state.attributes.get("unit_of_measurement")
        if unit == "kW":
            power *= 1000.0
        elif unit == "mW":
            power /= 1000.0
        elif unit not in (None, "W"):
            _LOGGER.warning("Dryer sensor %s uses unsupported power unit %s", entity_id, unit)
            return False
        return power >= float(self.options[OPT_DRYER_POWER_THRESHOLD])

    def _fan_is_on(self) -> bool:
        state = self.hass.states.get(self.fan_entity)
        return state is not None and state.state == STATE_ON

    def _required_delta(self, indoor_rh: float, dryer_active: bool) -> float:
        opts = self.options
        if indoor_rh >= float(opts[OPT_HUMIDITY_HIGH]):
            required = float(opts[OPT_DELTA_HIGH])
        elif indoor_rh >= float(opts[OPT_HUMIDITY_MEDIUM]):
            required = float(opts[OPT_DELTA_MEDIUM])
        else:
            required = float(opts[OPT_DELTA_LOW])
        if dryer_active:
            required = max(float(opts[OPT_STOP_DELTA]) + 0.1, required - float(opts[OPT_DRYER_BONUS]))
        return required

    def _elapsed_minutes(self, since: datetime | None) -> float | None:
        if since is None:
            return None
        return (dt_util.utcnow() - since).total_seconds() / 60.0

    async def _async_set_fan(self, turn_on: bool) -> None:
        domain = self.fan_entity.split(".", 1)[0]
        service = "turn_on" if turn_on else "turn_off"
        if domain not in ("fan", "switch"):
            _LOGGER.error("Unsupported fan entity domain: %s", domain)
            return
        if self._fan_is_on() == turn_on:
            return
        await self.hass.services.async_call(
            domain,
            service,
            {"entity_id": self.fan_entity},
            blocking=True,
        )
        now = dt_util.utcnow()
        if turn_on:
            self._last_on = now
        else:
            self._last_off = now

    async def async_set_mode(self, mode: str) -> None:
        """Set operating mode and evaluate immediately."""
        if mode not in (MODE_AUTOMATIC, MODE_OFF, MODE_MANUAL_ON):
            raise ValueError(f"Unknown mode: {mode}")
        self.mode = mode
        await self.async_evaluate()

    async def async_evaluate(self) -> None:
        """Calculate ventilation conditions and operate the fan when required."""
        indoor_t = self._numeric_state(self.entry.data[CONF_INDOOR_TEMPERATURE])
        indoor_rh = self._numeric_state(self.entry.data[CONF_INDOOR_HUMIDITY])
        outdoor_t = self._numeric_state(self.entry.data[CONF_OUTDOOR_TEMPERATURE])
        outdoor_rh = self._numeric_state(self.entry.data[CONF_OUTDOOR_HUMIDITY])
        dryer_active = self._dryer_is_active(self.entry.data.get(CONF_DRYER_1)) or self._dryer_is_active(
            self.entry.data.get(CONF_DRYER_2)
        )

        snap = VentilationSnapshot(dryer_active=dryer_active)
        values = (indoor_t, indoor_rh, outdoor_t, outdoor_rh)
        if any(value is None for value in values):
            snap.status = "Gesperrt"
            snap.reason = "Mindestens ein benötigter Temperatur- oder Feuchtesensor ist nicht verfügbar"
            self.snapshot = snap
            if self.mode != MODE_MANUAL_ON:
                await self._async_set_fan(False)
            async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)
            return

        assert indoor_t is not None and indoor_rh is not None and outdoor_t is not None and outdoor_rh is not None
        if not (0.0 <= indoor_rh <= 100.0 and 0.0 <= outdoor_rh <= 100.0):
            snap.status = "Gesperrt"
            snap.reason = "Unplausibler Luftfeuchtewert außerhalb 0–100 %"
            self.snapshot = snap
            if self.mode != MODE_MANUAL_ON:
                await self._async_set_fan(False)
            async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)
            return

        snap.sensors_ok = True
        snap.indoor_absolute_humidity = absolute_humidity_g_m3(indoor_t, indoor_rh)
        snap.outdoor_absolute_humidity = absolute_humidity_g_m3(outdoor_t, outdoor_rh)
        snap.humidity_delta = snap.indoor_absolute_humidity - snap.outdoor_absolute_humidity
        snap.indoor_dew_point = dew_point_c(indoor_t, indoor_rh)
        snap.outdoor_dew_point = dew_point_c(outdoor_t, outdoor_rh)
        snap.required_delta = self._required_delta(indoor_rh, dryer_active)

        fan_on = self._fan_is_on()
        min_runtime = float(self.options[OPT_MIN_RUNTIME])
        min_pause = float(self.options[OPT_MIN_PAUSE])
        max_runtime = float(self.options[OPT_MAX_RUNTIME])

        if self.mode == MODE_OFF:
            snap.status = "Aus"
            snap.reason = "Betriebsart Aus"
            await self._async_set_fan(False)
        elif self.mode == MODE_MANUAL_ON:
            snap.status = "Manuell"
            snap.reason = "Lüfter wurde manuell eingeschaltet"
            await self._async_set_fan(True)
        elif indoor_rh < float(self.options[OPT_MIN_HUMIDITY]):
            snap.status = "Warten"
            snap.reason = f"Kellerfeuchte {indoor_rh:.1f} % liegt unter der Mindestfeuchte"
            if fan_on and (self._elapsed_minutes(self._last_on) or min_runtime) < min_runtime:
                snap.reason = "Mindestlaufzeit läuft noch"
            else:
                await self._async_set_fan(False)
        elif fan_on:
            snap.ventilation_useful = snap.humidity_delta > float(self.options[OPT_STOP_DELTA])
            elapsed_on = self._elapsed_minutes(self._last_on)
            if elapsed_on is not None and elapsed_on < min_runtime:
                snap.status = "Lüften"
                snap.reason = "Mindestlaufzeit läuft noch"
            elif max_runtime > 0 and elapsed_on is not None and elapsed_on >= max_runtime:
                snap.status = "Pause"
                snap.reason = "Optionale maximale Laufzeit erreicht"
                await self._async_set_fan(False)
            elif snap.humidity_delta <= float(self.options[OPT_STOP_DELTA]):
                snap.status = "Warten"
                snap.reason = f"Entfeuchtungsvorteil nur noch {snap.humidity_delta:.2f} g/m³"
                await self._async_set_fan(False)
            else:
                snap.status = "Lüften"
                snap.reason = f"Außenluft ist {snap.humidity_delta:.2f} g/m³ trockener als Kellerluft"
        else:
            snap.ventilation_useful = snap.humidity_delta >= snap.required_delta
            elapsed_off = self._elapsed_minutes(self._last_off)
            if elapsed_off is not None and elapsed_off < min_pause:
                snap.status = "Pause"
                snap.reason = "Mindestpause läuft noch"
            elif snap.humidity_delta >= snap.required_delta:
                snap.status = "Lüften"
                suffix = " (Trockner aktiv)" if dryer_active else ""
                snap.reason = f"Außenluft ist {snap.humidity_delta:.2f} g/m³ trockener als Kellerluft{suffix}"
                await self._async_set_fan(True)
            else:
                snap.status = "Warten"
                snap.reason = (
                    f"Entfeuchtungsvorteil {snap.humidity_delta:.2f} g/m³; "
                    f"benötigt werden {snap.required_delta:.2f} g/m³"
                )

        self.snapshot = snap
        async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)
