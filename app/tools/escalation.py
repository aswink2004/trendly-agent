from typing import Any


def escalate_to_human(
    reason: str,
    customer_message: str,
    order_id: str | None = None,
    checks_performed: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a structured handoff for a human support agent.
    """

    return {
        "status": "escalated",
        "reason": reason,
        "order_id": order_id,
        "customer_message": customer_message,
        "checks_performed": checks_performed or [],
        "recommended_next_action": (
            "Human support agent should review and resolve the issue."
        ),
    }