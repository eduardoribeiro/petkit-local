"""Verified T4 Finish Litter Calibration behavior."""
from __future__ import annotations

import time

import pytest

from petkit_local.devices.base import Device, Refused
from petkit_local.events import codes, decode
from petkit_local.events.normalize import apply_derived_state, apply_state_snapshot
from petkit_local.ha.categories import get_entities_for_device
from petkit_local.ha.commands import ALL_ACTIONS


def _ready_t4() -> Device:
    device = Device(device_type="t4", petkit_id=1, online=True)
    device.state = {"workingState": -1, "petInTime": 0}
    return device


def test_t4_finish_calibration_command_and_entity_are_model_scoped():
    device = _ready_t4()
    suffix, envelope = ALL_ACTIONS["finish_litter_calibration"](device)
    assert suffix == "start"
    assert envelope["params"] == {"start_action": 6}
    assert "finish_litter_calibration" in {e.key for e in get_entities_for_device(device)}
    status = next(e for e in get_entities_for_device(device) if e.key == "device_status")
    assert status.options[status.option_values.index(6)] == "litter calibration"
    for model in ("t3", "t5", "t6", "d4s"):
        other = Device(device_type=model, petkit_id=2)
        assert "finish_litter_calibration" not in {e.key for e in get_entities_for_device(other)}
        with pytest.raises(Refused):
            ALL_ACTIONS["finish_litter_calibration"](other)


@pytest.mark.parametrize("state", [
    {"workingState": 0, "petInTime": 0},
    {"workingState": -1, "petInTime": 1},
    {},
])
def test_t4_finish_calibration_refuses_busy_occupied_and_unknown_state(state):
    device = _ready_t4()
    device.state = state
    with pytest.raises(Refused):
        ALL_ACTIONS["finish_litter_calibration"](device)


def test_t4_calibration_result_has_its_own_meaning():
    assert codes.lookup("18", "t4").role == codes.ROLE_DONE
    assert codes.work_modes_for("t4")[6] == "litter calibration"
    assert codes.work_modes_for("t5")[6] == "reset deodorant"
    label = decode.event_label("18", {"result": 1, "start_reason": 2}, "t4")
    assert "completed" in label and "terminated" not in label


def test_t4_completion_clears_a_retained_mode_without_inventing_telemetry():
    device = Device(device_type="t4", petkit_id=1)
    now = time.time()
    device.state = {"workingState": 6, "sandPercent": 16, "usedTimes": 71}
    apply_derived_state(device, "3", {"action": 6}, event_time=now)
    apply_derived_state(device, "18", {"result": 1}, event_time=now + 2)
    assert device.state["workingState"] == -1
    assert device.state["sandPercent"] == 16
    assert device.state["usedTimes"] == 71
    apply_state_snapshot(device, {"workState": {"workMode": 6}})
    assert device.state["workingState"] == -1


def test_late_completion_does_not_finish_a_newer_t4_calibration():
    device = Device(device_type="t4", petkit_id=1)
    now = time.time()
    apply_derived_state(device, "3", {"action": 6}, event_time=now)
    apply_derived_state(device, "18", {"result": 1}, event_time=now + 2)
    apply_derived_state(device, "3", {"action": 6}, event_time=now + 10)
    apply_derived_state(device, "18", {"result": 1}, event_time=now + 2)
    assert device.state["workingState"] == 6
