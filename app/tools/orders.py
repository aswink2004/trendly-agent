import json
from pathlib import Path
from typing import Any


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "orders.json"
)


def load_orders() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)

#looks eactly for specific order
def lookup_order(order_id: str) -> dict[str, Any] | None:
   

    order_id = order_id.strip().upper()

    data = load_orders()

    for order in data["orders"]:
        if order["order_id"].upper() == order_id:
            return order

    return None