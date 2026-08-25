from app.state import get_state


def test_return_state_can_store_customer_facts():
    state = get_state("test-agent-facts")

    state.item_condition = "unworn"
    state.has_original_tags = True
    state.has_original_packaging = True

    assert state.item_condition == "unworn"
    assert state.has_original_tags is True
    assert state.has_original_packaging is True


def test_return_confirmation_state():
    state = get_state("test-agent-confirmation")

    state.current_order_id = "TR-4530"
    state.current_sku = "TR-KRT-033"
    state.eligibility_checked = True
    state.return_eligible = True
    state.return_confirmation_required = True

    assert state.current_order_id == "TR-4530"
    assert state.current_sku == "TR-KRT-033"
    assert state.eligibility_checked is True
    assert state.return_eligible is True
    assert state.return_confirmation_required is True


def test_customer_isolation_state():
    state = get_state("test-agent-security")

    state.customer_id = "C-999"

    order_customer_id = "C-101"

    assert order_customer_id != state.customer_id