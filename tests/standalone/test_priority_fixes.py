"""Regression checks for the four priority fixes without an installed HA runtime.

Run: python3 -m unittest discover -s tests/standalone -v

The production classes are executed unchanged, with imports replaced by explicit
HA test doubles. This covers control decisions and call ordering, not a full HA
installation, frontend, real storage I/O, or the platform manager itself.
"""

from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/kellerlueftung"


def callback(fn):
    fn._hass_callback = True
    return fn


def load_source(name, path, injected=None, selected=None):
    """Execute the original definitions, avoiding HA imports and the type alias."""
    tree = ast.parse(path.read_text())
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and (
            node.level or node.module == "__future__"
            or (node.module or "").startswith("homeassistant")
        )
    ) and not isinstance(node, ast.TypeAlias)]
    if selected is not None:
        tree.body = [node for node in tree.body if getattr(node, "name", None) in selected]
    tree.body.insert(0, ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0
    ))
    ast.fix_missing_locations(tree)
    module = ModuleType(name)
    module.__dict__.update({key: value for key, value in (injected or {}).items()
                            if not key.startswith("__")})
    sys.modules[name] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


class FakeStore:
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, hass, version, key, **kwargs):
        self.hass, self.key = hass, key

    async def async_load(self):
        await asyncio.sleep(0)
        return deepcopy(self.hass.storage.get(self.key))

    async def async_save(self, data):
        await asyncio.sleep(0)
        if self.hass.fail_storage:
            raise OSError("Simulated storage failure")
        self.hass.storage[self.key] = deepcopy(data)

    async def async_remove(self):
        self.hass.storage.pop(self.key, None)


class FakeEntity:
    async def async_added_to_hass(self):
        pass

    def async_on_remove(self, fn):
        self.hass.entity_cleanup.append(fn)

    def async_write_ha_state(self):
        if asyncio.get_running_loop() is not self.hass.loop:
            raise RuntimeError("State write outside the event loop")
        self.hass.writes.append(self)


class FakeSelectEntity(FakeEntity):
    pass


class FakeRestoreEntity(FakeEntity):
    async def async_get_last_state(self):
        await asyncio.sleep(0)
        self.hass.legacy_restore_calls += 1
        return self.hass.previous_select


def dispatcher_connect(hass, signal, target):
    hass.receivers.append(target)
    return lambda: hass.receivers.remove(target)


def dispatcher_send(hass, signal, entry_id):
    for target in list(hass.receivers):
        if getattr(target, "_hass_callback", False):
            target(entry_id)
        else:
            raise AssertionError("Dispatcher target would run in an executor")


def subscribe(hass, *args):
    listener = object()
    hass.listeners.append(listener)
    return lambda: hass.listeners.remove(listener)


calc = load_source("_keller_regression_calc", SOURCE / "calculations.py")
const = load_source("_keller_regression_const", SOURCE / "const.py", {
    "Platform": SimpleNamespace(SENSOR="sensor", BINARY_SENSOR="binary_sensor", SELECT="select")
})
controller_module = load_source("_keller_regression_controller", SOURCE / "controller.py", {
    **vars(const), **vars(calc), "Store": FakeStore, "callback": callback,
    "dt_util": SimpleNamespace(utcnow=lambda: datetime.now(timezone.utc)),
    "async_dispatcher_connect": dispatcher_connect, "async_dispatcher_send": dispatcher_send,
    "async_track_state_change_event": subscribe, "async_track_time_interval": subscribe,
    "STATE_ON": "on", "STATE_UNKNOWN": "unknown", "STATE_UNAVAILABLE": "unavailable",
})
entity_module = load_source("_keller_regression_entity", SOURCE / "entity.py", {
    **vars(const), "callback": callback, "Entity": FakeEntity,
    "DeviceInfo": lambda **kwargs: kwargs, "async_dispatcher_connect": dispatcher_connect,
})
select_module = load_source("_keller_regression_select", SOURCE / "select.py", {
    **vars(const), "KellerlueftungEntity": entity_module.KellerlueftungEntity,
    "SelectEntity": FakeSelectEntity, "RestoreEntity": FakeRestoreEntity,
})
setup_module = load_source("_keller_regression_setup", SOURCE / "__init__.py", {
    **vars(const), "KellerlueftungController": controller_module.KellerlueftungController,
    "mode_storage": controller_module.mode_storage,
})


class FakeFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}


class FakeOptionsFlow(FakeFlow):
    @property
    def config_entry(self):
        # Mirrors the read-only public OptionsFlow property in current HA.
        return self.hass.config_entries.async_get_known_entry(self.handler)


flow_module = load_source("_keller_regression_flow", SOURCE / "config_flow.py", {
    **vars(const), "callback": callback,
    "config_entries": SimpleNamespace(ConfigFlow=FakeFlow, OptionsFlow=FakeOptionsFlow),
    "_options_schema": lambda data: deepcopy(data),
}, selected={"KellerlueftungConfigFlow", "KellerlueftungOptionsFlow", "_validate_options"})


class FakeHass:
    def __init__(self, fan="off", saved_mode=None, previous_mode=None, select_enabled=True):
        self.loop = asyncio.get_running_loop()
        self.storage = {}
        if saved_mode is not None:
            self.storage["kellerlueftung.audit.mode"] = {"mode": saved_mode}
        self.fail_storage = False
        self.previous_select = SimpleNamespace(state=previous_mode) if previous_mode else None
        self.select_enabled = select_enabled
        self.legacy_restore_calls = 0
        self.values = {
            "sensor.indoor_t": SimpleNamespace(state="20", attributes={"unit_of_measurement": "°C"}),
            "sensor.indoor_rh": SimpleNamespace(state="80", attributes={"unit_of_measurement": "%"}),
            "sensor.outdoor_t": SimpleNamespace(state="10", attributes={"unit_of_measurement": "°C"}),
            "sensor.outdoor_rh": SimpleNamespace(state="50", attributes={"unit_of_measurement": "%"}),
            "switch.fan": SimpleNamespace(state=fan, attributes={}),
        }
        self.states = SimpleNamespace(get=self.values.get)
        self.calls, self.writes, self.receivers, self.listeners, self.entity_cleanup = [], [], [], [], []
        self.forwarding_done = False
        self.services = SimpleNamespace(async_call=self.call)
        self.async_create_task = asyncio.create_task
        self.entry = SimpleNamespace(
            entry_id="audit", data={
                const.CONF_INDOOR_TEMPERATURE: "sensor.indoor_t",
                const.CONF_INDOOR_HUMIDITY: "sensor.indoor_rh",
                const.CONF_OUTDOOR_TEMPERATURE: "sensor.outdoor_t",
                const.CONF_OUTDOOR_HUMIDITY: "sensor.outdoor_rh",
                const.CONF_FAN_ENTITY: "switch.fan",
            }, options={}, async_on_unload=lambda fn: None,
            add_update_listener=lambda fn: lambda: None,
        )
        self.config_entries = SimpleNamespace(
            async_forward_entry_setups=self.forward,
            async_get_known_entry=lambda entry_id: self.entry,
        )

    async def call(self, domain, service, data, blocking):
        self.calls.append((service, self.forwarding_done))
        self.values[data["entity_id"]].state = "on" if service == "turn_on" else "off"

    async def forward(self, entry, platforms):
        if self.select_enabled:
            self.mode_select = select_module.KellerModeSelect(entry)
            self.mode_select.hass = self
            await self.mode_select.async_added_to_hass()
        self.forwarding_done = True

    async def setup(self):
        await setup_module.async_setup_entry(self, self.entry)
        return self.entry.runtime_data


class PriorityFixTests(unittest.IsolatedAsyncioTestCase):
    async def test_options_factory_and_read_only_property(self):
        hass = FakeHass()
        hass.entry.options = {const.OPT_MIN_HUMIDITY: 68}
        flow = flow_module.KellerlueftungConfigFlow.async_get_options_flow(hass.entry)
        flow.hass, flow.handler = hass, "audit"
        self.assertIs(flow.config_entry, hass.entry)
        result = await flow.async_step_init()
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["data_schema"][const.OPT_MIN_HUMIDITY], 68)
        self.assertTrue(getattr(flow_module.KellerlueftungConfigFlow.async_get_options_flow, "_hass_callback", False))

    async def test_options_save_and_invalid_order(self):
        flow = flow_module.KellerlueftungOptionsFlow()
        flow.hass, flow.handler = FakeHass(), "audit"
        valid = dict(const.DEFAULTS)
        result = await flow.async_step_init(valid)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"], valid)
        invalid = {**valid, const.OPT_MIN_HUMIDITY: 80}
        result = await flow.async_step_init(invalid)
        self.assertEqual(result["errors"], {"base": "humidity_order"})

    async def test_dispatcher_updates_in_event_loop_for_matching_entry_only(self):
        hass = FakeHass(saved_mode=const.MODE_OFF)
        ctrl = await hass.setup()
        entity = entity_module.KellerlueftungEntity(hass.entry)
        entity.hass = hass
        await entity.async_added_to_hass()
        self.assertTrue(getattr(entity._handle_controller_update, "_hass_callback", False))
        hass.writes.clear()
        dispatcher_send(hass, const.SIGNAL_UPDATE, "other-entry")
        self.assertEqual(hass.writes, [])
        await ctrl.async_evaluate()
        self.assertIn(entity, hass.writes)

    async def test_legacy_off_does_not_emit_start_pulse(self):
        hass = FakeHass(previous_mode=const.MODE_OFF)
        ctrl = await hass.setup()
        self.assertEqual(hass.calls, [])
        self.assertEqual(ctrl.mode, const.MODE_OFF)
        self.assertEqual(hass.storage["kellerlueftung.audit.mode"], {"mode": const.MODE_OFF})

    async def test_legacy_manual_on_starts_only_after_restoration(self):
        hass = FakeHass(previous_mode=const.MODE_MANUAL_ON)
        ctrl = await hass.setup()
        self.assertEqual(ctrl.mode, const.MODE_MANUAL_ON)
        self.assertEqual(hass.calls, [("turn_on", True)])

    async def test_new_install_still_defaults_to_automatic(self):
        hass = FakeHass()
        ctrl = await hass.setup()
        self.assertEqual(ctrl.mode, const.MODE_AUTOMATIC)
        self.assertEqual(hass.calls, [("turn_on", True)])

    async def test_stored_mode_precedes_old_select_state(self):
        hass = FakeHass(saved_mode=const.MODE_OFF, previous_mode=const.MODE_AUTOMATIC)
        await hass.setup()
        self.assertEqual(hass.calls, [])
        self.assertEqual(hass.legacy_restore_calls, 0)
        self.assertEqual(hass.mode_select._attr_current_option, const.MODE_OFF)

    async def test_disabled_select_preserves_stored_mode(self):
        for mode, expected in [(const.MODE_OFF, []), (const.MODE_AUTOMATIC, [("turn_on", True)])]:
            with self.subTest(mode=mode):
                hass = FakeHass(saved_mode=mode, select_enabled=False)
                ctrl = await hass.setup()
                self.assertEqual(ctrl.mode, mode)
                self.assertEqual(hass.calls, expected)

    async def test_missing_mode_with_disabled_select_blocks_and_turns_off(self):
        hass = FakeHass(fan="on", select_enabled=False)
        ctrl = await hass.setup()
        self.assertFalse(ctrl.mode_restored)
        self.assertEqual(ctrl.snapshot.status, "Gesperrt")
        self.assertEqual(hass.calls, [("turn_off", True)])
        self.assertNotIn("kellerlueftung.audit.mode", hass.storage)

    async def test_mode_changes_before_start_never_switch_fan(self):
        hass = FakeHass()
        ctrl = controller_module.KellerlueftungController(hass, hass.entry)
        await ctrl.async_set_mode(const.MODE_AUTOMATIC)
        await ctrl.async_evaluate()
        self.assertEqual(hass.calls, [])
        hass.forwarding_done = True
        await ctrl.async_start()
        self.assertEqual(hass.calls, [("turn_on", True)])

    async def test_selected_off_survives_reload(self):
        hass = FakeHass(saved_mode=const.MODE_AUTOMATIC)
        ctrl = await hass.setup()
        await hass.mode_select.async_select_option(const.MODE_OFF)
        self.assertEqual(hass.storage["kellerlueftung.audit.mode"], {"mode": const.MODE_OFF})
        await ctrl.async_stop()
        for fn in hass.entity_cleanup:
            fn()
        hass.entity_cleanup.clear()
        hass.calls.clear()
        await hass.setup()
        self.assertEqual(hass.calls, [])
        self.assertEqual(hass.entry.runtime_data.mode, const.MODE_OFF)

    async def test_save_failure_does_not_change_mode_or_display(self):
        hass = FakeHass(saved_mode=const.MODE_OFF)
        ctrl = await hass.setup()
        hass.fail_storage = True
        with self.assertRaises(OSError):
            await hass.mode_select.async_select_option(const.MODE_AUTOMATIC)
        self.assertEqual(ctrl.mode, const.MODE_OFF)
        self.assertEqual(hass.mode_select._attr_current_option, const.MODE_OFF)
        self.assertEqual(hass.calls, [])

    async def test_removing_entry_removes_its_persisted_mode(self):
        hass = FakeHass(saved_mode=const.MODE_OFF)
        await setup_module.async_remove_entry(hass, hass.entry)
        self.assertNotIn("kellerlueftung.audit.mode", hass.storage)

    async def test_invalid_temperatures_stop_automatic_fan(self):
        for sensor in ["sensor.indoor_t", "sensor.outdoor_t"]:
            for value in ["nan", "inf", "-inf", "-273.15", "-272.62", "-101", "101", "1e999", "unavailable", "unknown", "broken"]:
                with self.subTest(sensor=sensor, value=value):
                    hass = FakeHass(fan="on", saved_mode=const.MODE_AUTOMATIC)
                    hass.values[sensor].state = value
                    ctrl = await hass.setup()
                    self.assertEqual(hass.values["switch.fan"].state, "off")
                    self.assertFalse(ctrl.snapshot.sensors_ok)
                    self.assertEqual(ctrl.snapshot.status, "Gesperrt")
                    self.assertIsNone(ctrl.snapshot.indoor_absolute_humidity)

    async def test_invalid_humidity_stops_automatic_fan(self):
        for sensor in ["sensor.indoor_rh", "sensor.outdoor_rh"]:
            for value in ["nan", "inf", "-inf", "-1", "101"]:
                with self.subTest(sensor=sensor, value=value):
                    hass = FakeHass(fan="on", saved_mode=const.MODE_AUTOMATIC)
                    hass.values[sensor].state = value
                    ctrl = await hass.setup()
                    self.assertEqual(hass.values["switch.fan"].state, "off")
                    self.assertFalse(ctrl.snapshot.sensors_ok)

    async def test_sensor_failure_overrides_minimum_runtime(self):
        hass = FakeHass(saved_mode=const.MODE_AUTOMATIC)
        ctrl = await hass.setup()
        self.assertEqual(hass.values["switch.fan"].state, "on")
        hass.values["sensor.indoor_t"].state = "nan"
        await ctrl.async_evaluate()
        self.assertEqual(hass.values["switch.fan"].state, "off")
        self.assertFalse(ctrl.snapshot.sensors_ok)

    async def test_calculation_errors_stop_automatic_fan(self):
        for error in [OverflowError, ZeroDivisionError, ValueError]:
            with self.subTest(error=error.__name__):
                hass = FakeHass(fan="on", saved_mode=const.MODE_AUTOMATIC)
                with patch.object(controller_module, "absolute_humidity_g_m3", side_effect=error("bad calculation")):
                    ctrl = await hass.setup()
                self.assertEqual(hass.values["switch.fan"].state, "off")
                self.assertFalse(ctrl.snapshot.sensors_ok)

    async def test_nonfinite_calculation_results_are_not_published(self):
        for fn in ["absolute_humidity_g_m3", "dew_point_c"]:
            for value in [float("nan"), float("inf")]:
                with self.subTest(fn=fn, value=value):
                    hass = FakeHass(fan="on", saved_mode=const.MODE_AUTOMATIC)
                    with patch.object(controller_module, fn, return_value=value):
                        ctrl = await hass.setup()
                    self.assertFalse(ctrl.snapshot.sensors_ok)
                    self.assertIsNone(ctrl.snapshot.indoor_absolute_humidity)
                    self.assertIsNone(ctrl.snapshot.indoor_dew_point)
                    self.assertEqual(hass.values["switch.fan"].state, "off")

    async def test_manual_override_is_not_forcibly_stopped_on_sensor_failure(self):
        hass = FakeHass(fan="on", saved_mode=const.MODE_MANUAL_ON)
        hass.values["sensor.indoor_t"].state = "nan"
        ctrl = await hass.setup()
        self.assertEqual(hass.values["switch.fan"].state, "on")
        self.assertFalse(ctrl.snapshot.sensors_ok)
        self.assertEqual(hass.calls, [])

    async def test_valid_readings_and_temperature_bounds_are_accepted(self):
        for temperature in [str(const.MIN_TEMPERATURE_C), "20", str(const.MAX_TEMPERATURE_C)]:
            with self.subTest(temperature=temperature):
                hass = FakeHass(saved_mode=const.MODE_AUTOMATIC)
                hass.values["sensor.indoor_t"].state = temperature
                ctrl = await hass.setup()
                self.assertTrue(ctrl.snapshot.sensors_ok)
        self.assertAlmostEqual(calc.absolute_humidity_g_m3(20, 50), 8.64, delta=.05)
        self.assertAlmostEqual(calc.dew_point_c(20, 50), 9.26, delta=.1)

    async def test_mode_and_diagnostics_recover_after_sensor_failure(self):
        hass = FakeHass(saved_mode=const.MODE_AUTOMATIC)
        hass.values["sensor.indoor_t"].state = "nan"
        ctrl = await hass.setup()
        hass.values["sensor.indoor_t"].state = "20"
        await ctrl.async_evaluate()
        self.assertTrue(ctrl.snapshot.sensors_ok)
        self.assertEqual(hass.values["switch.fan"].state, "on")

    async def test_stopped_controller_does_not_process_queued_evaluation(self):
        hass = FakeHass(saved_mode=const.MODE_AUTOMATIC)
        ctrl = await hass.setup()
        await ctrl.async_stop()
        hass.calls.clear()
        hass.values["sensor.indoor_t"].state = "nan"
        await ctrl._async_scheduled_evaluate()
        self.assertEqual(hass.calls, [])
        self.assertEqual(hass.listeners, [])

    async def test_sources_compile_and_json_versions_match(self):
        for path in ROOT.rglob("*.py"):
            compile(path.read_text(), str(path), "exec")
        for path in ROOT.rglob("*.json"):
            json.loads(path.read_text())
        manifest = json.loads((SOURCE / "manifest.json").read_text())
        self.assertEqual(manifest["version"], const.VERSION)


if __name__ == "__main__":
    unittest.main()
