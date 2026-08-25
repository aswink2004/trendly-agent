from app.tools.orders import lookup_order
from app.tools.policy import search_policy
from app.tools.returns import check_return_eligibility
from app.tools.escalation import escalate_to_human


def test_known_order():
    order = lookup_order("TR-4530")

    assert order is not None
    assert order["order_id"] == "TR-4530"
    assert order["status"] == "delivered"


def test_unknown_order():
    order = lookup_order("TR-9999")

    assert order is None


def test_policy_return_window():
    result = search_policy("return window")

    assert result["found"] is True

    policy_text = "\n".join(
        result["matches"]
    ).lower()

    assert "30 calendar days" in policy_text


def test_policy_lost_parcel():
    result = search_policy("lost parcel")

    assert result["found"] is True

    policy_text = "\n".join(
        result["matches"]
    ).lower()

    assert "human" in policy_text


# -----------------------------
# Return eligibility tests
# -----------------------------

def test_happy_path_return():
    result = check_return_eligibility(
        order_id="TR-4530",
        sku="TR-KRT-033",
        condition="unworn",
        has_original_tags=True,
        current_date="2026-08-24",
    )

    assert result["eligible"] is True
    assert result["decision"] == "eligible"


def test_expired_return():
    result = check_return_eligibility(
        order_id="TR-4523",
        sku="TR-JKT-008",
        current_date="2026-08-24",
    )

    assert result["eligible"] is False
    assert result["decision"] == "not_eligible"


def test_jewellery_not_returnable():
    result = check_return_eligibility(
        order_id="TR-4527",
        sku="TR-EAR-042",
        current_date="2026-08-24",
    )

    assert result["eligible"] is False
    assert result["decision"] == "not_eligible"


# def test_final_sale_exchange_only():
#     result = check_return_eligibility(
#         order_id="TR-4528",
#         sku="TR-SHR-009",
#         current_date="2026-08-24",
#     )

#     assert result["eligible"] is False
#     assert result["decision"] == "exchange_only"

def test_final_sale_exchange_only():
    result = check_return_eligibility(
        order_id="TR-4528",
        sku="TR-SHR-009",
        current_date="2026-08-18",
    )

    assert result["eligible"] is False
    assert result["decision"] == "exchange_only"


def test_cancelled_order():
    result = check_return_eligibility(
        order_id="TR-4529",
        sku="TR-SCF-027",
        current_date="2026-08-24",
    )

    assert result["eligible"] is False
    assert result["decision"] == "not_eligible"


def test_lost_parcel_requires_human():
    result = check_return_eligibility(
        order_id="TR-4526",
        sku="TR-BAG-011",
        current_date="2026-08-24",
    )

    assert result["eligible"] is False
    assert result["decision"] == "human"


def test_missing_tags():
    result = check_return_eligibility(
        order_id="TR-4530",
        sku="TR-KRT-033",
        condition="unworn",
        has_original_tags=False,
        current_date="2026-08-24",
    )

    assert result["eligible"] is False
    assert result["decision"] == "not_eligible"


def test_footwear_without_box():
    result = check_return_eligibility(
        order_id="TR-4525",
        sku="TR-SNK-017",
        condition="unworn",
        has_original_tags=True,
        has_original_packaging=False,
        current_date="2026-08-24",
    )

    # This order has not been delivered, so it should
    # not yet be eligible for a return.
    assert result["eligible"] is False

def test_human_escalation():
    result = escalate_to_human(
        reason="Lost parcel",
        customer_message="My package never arrived.",
        order_id="TR-4526",
        checks_performed=[
            "Order lookup",
            "Carrier status checked",
        ],
    )

    assert result["status"] == "escalated"
    assert result["reason"] == "Lost parcel"
    assert result["order_id"] == "TR-4526"
    assert "Order lookup" in result["checks_performed"]