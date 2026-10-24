"""The scenario returns only what it switched, unless told to switch everything off.

The snapshot taken at the start describes the devices the scenario actually drove.
Restoring it after the scenario finishes must therefore leave alone a device a
person turned on while the scenario ran, while the explicitly named behaviour
"switch everything off" keeps meaning the whole home.
"""

from datetime import UTC, datetime

from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.entities.scenario.scenario_action import ScenarioAction
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_channel import RelayChannel
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from tests.conftest import OWNER_UUID, make_device

NOW = datetime(2027, 6, 1, 12, 0, tzinfo=UTC)


def running_scenario(
    behavior: CompletionBehavior, captured: dict[DeviceId, DeviceStatus]
) -> Scenario:
    """Build a scenario that started with the given snapshot.

    Args:
        behavior: What the scenario does with the devices after finishing.
        captured: States the scenario took before switching anything.

    Returns:
        Scenario: Scenario in the running stage.
    """
    scenario = Scenario.schedule(
        user_id=UserId.parse(OWNER_UUID),
        created_at=NOW,
        actions=(ScenarioAction(capability=Capability.ON),),
        completion_behavior=behavior,
    )
    scenario.start(captured)
    return scenario


def test_restoring_leaves_devices_the_scenario_never_switched_alone() -> None:
    lamp = make_device()
    heater = make_device(channel=RelayChannel(2), name="Heater")
    scenario = running_scenario(
        CompletionBehavior.RESTORE_CAPTURED_STATE, {lamp.id: DeviceStatus.OFF}
    )

    restored = scenario.statuses_to_restore([lamp.id, heater.id])

    assert restored == {lamp.id: DeviceStatus.OFF}


def test_switching_everything_off_covers_the_whole_home() -> None:
    lamp = make_device()
    heater = make_device(channel=RelayChannel(2), name="Heater")
    scenario = running_scenario(
        CompletionBehavior.SWITCH_EVERYTHING_OFF, {lamp.id: DeviceStatus.ACTIVE}
    )

    restored = scenario.statuses_to_restore([lamp.id, heater.id])

    assert restored == {lamp.id: DeviceStatus.OFF, heater.id: DeviceStatus.OFF}


def test_leaving_to_automation_returns_nothing_to_restore() -> None:
    lamp = make_device()
    scenario = running_scenario(
        CompletionBehavior.LEAVE_TO_AUTOMATION, {lamp.id: DeviceStatus.ACTIVE}
    )

    assert scenario.statuses_to_restore([lamp.id]) == {}
