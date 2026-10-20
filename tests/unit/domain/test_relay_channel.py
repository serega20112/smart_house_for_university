import pytest

from smart_home.domain.devices.relay_channel import (
    FIRST_CHANNEL,
    PHYSICAL_RELAY_LIMIT,
    RelayChannel,
)
from smart_home.domain.exceptions import InvalidRelayChannelError


@pytest.mark.parametrize("number", [FIRST_CHANNEL, PHYSICAL_RELAY_LIMIT, 6, 15])
def test_relay_channel_with_number_in_range_is_valid(number: int) -> None:
    channel = RelayChannel(number)
    assert int(channel) == number
    assert channel.number == number


@pytest.mark.parametrize("number", [FIRST_CHANNEL - 1, PHYSICAL_RELAY_LIMIT + 1, 0, -1, 100])
def test_relay_channel_with_number_outside_the_hardware_is_refused(number: int) -> None:
    with pytest.raises(InvalidRelayChannelError):
        RelayChannel(number)


def test_relay_channel_order_follows_the_number() -> None:
    assert RelayChannel(1) < RelayChannel(2)
