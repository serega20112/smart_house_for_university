import pytest

from backend.domain.exceptions import InvalidRelayChannelError
from backend.domain.value_objects.devices.relay_channel import (
    FIRST_CHANNEL,
    RELAY_COUNT,
    RelayChannel,
)


@pytest.mark.parametrize("number", [FIRST_CHANNEL, RELAY_COUNT, RELAY_COUNT // 2])
def test_relay_channel_with_number_in_range_is_valid(number: int) -> None:
    channel = RelayChannel(number)
    assert int(channel) == number
    assert channel.number == number


@pytest.mark.parametrize("number", [FIRST_CHANNEL - 1, RELAY_COUNT + 1, 0, -1, 100])
def test_relay_channel_with_number_outside_the_hardware_is_refused(number: int) -> None:
    with pytest.raises(InvalidRelayChannelError):
        RelayChannel(number)


def test_relay_channel_order_follows_the_number() -> None:
    assert RelayChannel(1) < RelayChannel(2)
