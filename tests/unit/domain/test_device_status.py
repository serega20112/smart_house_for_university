import pytest

from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device_status import DeviceStatus


@pytest.mark.parametrize("capability", list(Capability))
def test_device_status_after_capability_resolves_every_member(
    capability: Capability,
) -> None:
    status = DeviceStatus.after(capability)

    assert isinstance(status, DeviceStatus)
    assert status is not DeviceStatus.UNAVAILABLE


@pytest.mark.parametrize("capability", list(Capability))
def test_device_status_restored_by_reverses_the_resulting_state(
    capability: Capability,
) -> None:
    status = DeviceStatus.after(capability)

    assert DeviceStatus.restored_by(status) is capability


@pytest.mark.parametrize("status", list(DeviceStatus))
def test_device_status_is_available_for_every_member_but_unavailable(
    status: DeviceStatus,
) -> None:
    assert status.is_available is (status is not DeviceStatus.UNAVAILABLE)


@pytest.mark.parametrize("status", list(DeviceStatus))
def test_device_status_is_active_matches_the_off_and_unavailable_states(
    status: DeviceStatus,
) -> None:
    expected = status not in (DeviceStatus.OFF, DeviceStatus.UNAVAILABLE)
    assert status.is_active is expected
