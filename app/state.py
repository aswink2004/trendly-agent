from dataclasses import dataclass, field


@dataclass
class ConversationState:
    conversation_id: str

    customer_id: str | None = None

    current_order_id: str | None = None

    current_sku: str | None = None

    pending_action: str | None = None

    item_condition: str | None = None

    has_original_tags: bool | None = None

    has_original_packaging: bool | None = None
    item_condition: str | None = None
    has_original_tags: bool | None = None
    has_original_packaging: bool | None = None
    eligibility_checked: bool = False

    return_eligible: bool = False

    return_confirmation_required: bool = False

    history: list[dict[str, str]] = field(
        default_factory=list
    )


_CONVERSATIONS: dict[
    str,
    ConversationState
] = {}


def get_state(
    conversation_id: str
) -> ConversationState:

    if conversation_id not in _CONVERSATIONS:

        _CONVERSATIONS[
            conversation_id
        ] = ConversationState(
            conversation_id=conversation_id
        )

    return _CONVERSATIONS[
        conversation_id
    ]


def reset_state(
    conversation_id: str
) -> None:

    _CONVERSATIONS.pop(
        conversation_id,
        None
    )