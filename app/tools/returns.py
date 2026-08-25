from datetime import datetime, timezone
from typing import Any

from .orders import lookup_order


NON_RETURNABLE_CATEGORIES = {
    "innerwear",
    "socks",
    "jewellery",
    "beauty",
    "fragrance",
    "face masks",
    "gift cards",
}


def parse_datetime(value: str) -> datetime:
    """
    Convert an ISO timestamp into a timezone-aware datetime.
    """
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def check_return_eligibility(
    order_id: str,
    sku: str,
    condition: str = "unknown",
    has_original_tags: bool | None = None,
    has_original_packaging: bool | None = None,
    current_date: str | None = None,
) -> dict[str, Any]:
    """
    Deterministically evaluate whether an item can be returned.

    The LLM does NOT make the eligibility decision.
    """

    # --------------------------------------------------
    # 1. Find order
    # --------------------------------------------------

    order = lookup_order(order_id)

    if not order:
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": "Order not found.",
        }

    # --------------------------------------------------
    # 2. Find item
    # --------------------------------------------------

    item = next(
        (
            item
            for item in order["items"]
            if item["sku"] == sku
        ),
        None,
    )

    if not item:
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": "Item not found in this order.",
        }

    # --------------------------------------------------
    # 3. Cancelled orders
    # --------------------------------------------------

    if order["status"] == "cancelled":
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": (
                "This order was cancelled. "
                "A return cannot be raised against a "
                "cancelled order."
            ),
        }

    # --------------------------------------------------
    # 4. Lost parcels
    # --------------------------------------------------

    if order["status"] == "lost_in_transit":
        return {
            "eligible": False,
            "decision": "human",
            "reason": (
                "This parcel is marked as lost in transit. "
                "It must be handled as a lost-parcel claim "
                "by a human support agent."
            ),
        }

    # --------------------------------------------------
    # 5. Must be delivered before return
    # --------------------------------------------------

    if not order.get("delivered_at"):
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": (
                "The item has not been delivered, "
                "so the return window has not started."
            ),
        }

    # --------------------------------------------------
    # 6. Calculate 30-day return window
    # --------------------------------------------------

    delivered_at = parse_datetime(
        order["delivered_at"]
    )

    if current_date:
        today = datetime.fromisoformat(
            current_date
        ).replace(tzinfo=timezone.utc)
    else:
        today = datetime.now(timezone.utc)

    days_since_delivery = (
        today.date() - delivered_at.date()
    ).days

    if days_since_delivery > 30:
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": (
                "The 30-calendar-day return window "
                "has expired."
            ),
            "days_since_delivery": days_since_delivery,
        }

    # --------------------------------------------------
    # 7. Final sale
    # --------------------------------------------------

    if item.get("final_sale") is True:
        return {
            "eligible": False,
            "decision": "exchange_only",
            "reason": (
                "This is a final-sale item. "
                "It is eligible for size exchange only, "
                "not a refund or store credit."
            ),
        }

    # --------------------------------------------------
    # 8. Non-returnable category
    # --------------------------------------------------

    category = item.get(
        "category",
        ""
    ).lower()

    if category in NON_RETURNABLE_CATEGORIES:
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": (
                f"The category '{item['category']}' "
                "is non-returnable for hygiene and "
                "safety reasons."
            ),
        }

    # --------------------------------------------------
    # 9. Condition
    # --------------------------------------------------

    if (
        condition != "unknown"
        and condition.lower()
        not in {"unworn", "unwashed"}
    ):
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": (
                "Returned items must be unworn "
                "and unwashed."
            ),
        }

    # --------------------------------------------------
    # 10. Original tags
    # --------------------------------------------------

    if has_original_tags is False:
        return {
            "eligible": False,
            "decision": "not_eligible",
            "reason": (
                "Original tags must be attached."
            ),
        }

    # --------------------------------------------------
    # 11. Footwear packaging
    # --------------------------------------------------

    if (
        category == "footwear"
        and has_original_packaging is False
    ):
        return {
            "eligible": True,
            "decision": "eligible_with_deduction",
            "reason": (
                "The footwear is returnable, but "
                "a ₹300 deduction applies because "
                "the original shoe box is missing."
            ),
            "deduction": 300,
        }

    # --------------------------------------------------
    # 12. Normal eligible return
    # --------------------------------------------------

    return {
        "eligible": True,
        "decision": "eligible",
        "reason": (
            "The item meets the known return rules."
        ),
    }


def create_return(order_id: str, sku: str,) -> dict[str, Any]:
    """
    Mock return action.

    In production this would call Trendly's OMS.
    """

    order = lookup_order(order_id)

    if not order:
        return {
            "success": False,
            "reason": "Order not found.",
        }

    item = next(
        (
            item
            for item in order["items"]
            if item["sku"] == sku
        ),
        None,
    )

    if not item:
        return {
            "success": False,
            "reason": "Item not found.",
        }

    return {
        "success": True,
        "action": "return_created",
        "order_id": order_id,
        "sku": sku,
    }


def create_exchange(
    order_id: str,
    sku: str,
    requested_size: str,
) -> dict[str, Any]:
    """
    Mock size-exchange action.

    The dataset does not provide inventory availability,
    so we must never invent availability.
    """

    order = lookup_order(order_id)

    if not order:
        return {
            "success": False,
            "reason": "Order not found.",
        }

    item = next(
        (
            item
            for item in order["items"]
            if item["sku"] == sku
        ),
        None,
    )

    if not item:
        return {
            "success": False,
            "reason": "Item not found.",
        }

    return {
        "success": True,
        "action": "exchange_requested",
        "order_id": order_id,
        "sku": sku,
        "requested_size": requested_size,
    }