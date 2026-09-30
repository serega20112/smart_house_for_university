"""Intent vocabulary of the natural language pipeline.

Both the classifier and the command router speak this language, so the canonical
intent names live in the domain layer together with the rest of the business
vocabulary.
"""

from __future__ import annotations

from smart_home_backend.domain.enums.base import StrEnum


class Intent(StrEnum):
    """Canonical user intent recognized from a free-form command."""

    TURN_ON = "TURN_ON"
    TURN_OFF = "TURN_OFF"
    TURN_ON_ALL = "TURN_ON_ALL"
    TURN_OFF_ALL = "TURN_OFF_ALL"

    SET_TEMPERATURE = "SET_TEMPERATURE"
    SET_HUMIDITY = "SET_HUMIDITY"

    COOL = "COOL"
    HEAT = "HEAT"

    GET_STATUS = "GET_STATUS"
    GET_TEMPERATURE = "GET_TEMPERATURE"
    GET_HUMIDITY = "GET_HUMIDITY"

    CREATE_SCENARIO = "CREATE_SCENARIO"
    CANCEL_SCENARIO = "CANCEL_SCENARIO"

    @property
    def changes_device_state(self) -> bool:
        """Return whether executing the intent affects physical devices.

        Intents that change the home require user confirmation when the
        classifier is not confident enough.

        Returns:
            bool: True for state-changing intents.
        """
        return self in ACTION_INTENTS

    @classmethod
    def parse(cls, raw: object) -> "Intent | None":
        """Parse an intent from an arbitrary value.

        Args:
            raw: Intent name or enum member.

        Returns:
            Intent | None: Parsed intent or None when the value is unknown.
        """
        if raw is None:
            return None
        if isinstance(raw, cls):
            return raw
        try:
            return cls(str(raw).strip().upper())
        except ValueError:
            return None


ACTION_INTENTS: frozenset[Intent] = frozenset(
    {
        Intent.TURN_ON,
        Intent.TURN_OFF,
        Intent.TURN_ON_ALL,
        Intent.TURN_OFF_ALL,
        Intent.SET_TEMPERATURE,
        Intent.SET_HUMIDITY,
        Intent.COOL,
        Intent.HEAT,
        Intent.CREATE_SCENARIO,
        Intent.CANCEL_SCENARIO,
    }
)

READ_INTENTS: frozenset[Intent] = frozenset(
    {
        Intent.GET_STATUS,
        Intent.GET_TEMPERATURE,
        Intent.GET_HUMIDITY,
    }
)
