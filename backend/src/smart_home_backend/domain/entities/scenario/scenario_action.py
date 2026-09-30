"""Single action inside a timed scenario."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.enums.device import Capability


@dataclass(frozen=True, slots=True)
class ScenarioAction:
    """One capability invocation requested by a scenario.

    The action is described by a capability and an optional target value rather
    than a relay number; the concrete device is chosen when the action runs.

    Args:
        capability: Capability to perform.
        target_value: Target climate value for the action, for example 20 degrees.

    Returns:
        None.
    """

    capability: Capability
    target_value: float | None = None

    def to_dict(self) -> dict:
        """Serialize the action into a plain dictionary.

        Returns:
            dict: Serialized action.
        """
        return {"capability": self.capability.value, "target_value": self.target_value}

    @classmethod
    def from_dict(cls, data: dict) -> "ScenarioAction":
        """Restore an action from its serialized form.

        Args:
            data: Serialized action.

        Returns:
            ScenarioAction: Restored action.
        """
        return cls(
            capability=Capability(data["capability"]),
            target_value=data.get("target_value"),
        )
