"""Reply to a free-form user command."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.enums.operation import ClarificationReason, OperationStatus


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Structured answer to a natural language command.

    Presentation renders the human readable text from this value, which keeps
    user-facing wording out of the application layer.

    Args:
        status: Result class of the command.
        intent: Recognized intent or None when it is unknown.
        confidence: Similarity of the closest reference phrase.
        clarification: Reason why the system needs more detail, if any.
        scenario_id: Identifier of the created scenario, when applicable.
        details: Additional structured data for rendering.

    Returns:
        None.
    """

    status: OperationStatus
    intent: str | None = None
    confidence: float = 1.0
    clarification: ClarificationReason | None = None
    scenario_id: int | None = None
    details: dict | None = None

    @property
    def ok(self) -> bool:
        """Return whether the command was executed.

        Returns:
            bool: True on success.
        """
        return self.status.is_success

    @classmethod
    def needs_clarification(
        cls,
        reason: ClarificationReason,
        intent: str | None = None,
        confidence: float = 0.0,
        **details: object,
    ) -> "CommandResult":
        """Build a reply asking the user for clarification.

        Args:
            reason: Why clarification is required.
            intent: Recognized intent or None.
            confidence: Similarity of the closest reference phrase.
            **details: Extra structured data for rendering.

        Returns:
            CommandResult: Clarification reply.
        """
        return cls(
            status=OperationStatus.INVALID_INPUT,
            intent=intent,
            confidence=confidence,
            clarification=reason,
            details=dict(details) if details else None,
        )
