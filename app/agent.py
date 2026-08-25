import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import SYSTEM_PROMPT
from .state import get_state

from .tools.orders import lookup_order
from .tools.policy import search_policy
from .tools.returns import (
    check_return_eligibility,
    create_return,
    create_exchange,
)
from .tools.escalation import escalate_to_human


load_dotenv()


MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


# --------------------------------------------------
# Gemini client
# --------------------------------------------------

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=api_key
    )


# --------------------------------------------------
# Tool declarations
# --------------------------------------------------

def get_tool_declarations():

    return [

        types.FunctionDeclaration(
            name="lookup_order",

            description=(
                "Look up an exact Trendly order "
                "using its order ID."
            ),

            parameters_json_schema={
                "type": "object",

                "properties": {
                    "order_id": {
                        "type": "string"
                    }
                },

                "required": [
                    "order_id"
                ],
            },
        ),

        types.FunctionDeclaration(
            name="search_policy",

            description=(
                "Search the supplied Trendly "
                "policy document for policy information."
            ),

            parameters_json_schema={
                "type": "object",

                "properties": {
                    "query": {
                        "type": "string"
                    }
                },

                "required": [
                    "query"
                ],
            },
        ),

        types.FunctionDeclaration(
            name="check_return_eligibility",

            description=(
                "Deterministically check whether "
                "an order item is eligible for return."
            ),

            parameters_json_schema={
                "type": "object",

                "properties": {

                    "order_id": {
                        "type": "string"
                    },

                    "sku": {
                        "type": "string"
                    },

                    "condition": {
                        "type": "string"
                    },

                    "has_original_tags": {
                        "type": "boolean"
                    },

                    "has_original_packaging": {
                        "type": "boolean"
                    },

                    "current_date": {
                        "type": "string"
                    },
                },

                "required": [
                    "order_id",
                    "sku",
                ],
            },
        ),

        types.FunctionDeclaration(
            name="create_return",

            description=(
                "Create a return request after "
                "eligibility has been confirmed "
                "and the customer explicitly "
                "authorizes the action."
            ),

            parameters_json_schema={
                "type": "object",

                "properties": {

                    "order_id": {
                        "type": "string"
                    },

                    "sku": {
                        "type": "string"
                    },
                },

                "required": [
                    "order_id",
                    "sku",
                ],
            },
        ),

        types.FunctionDeclaration(
            name="create_exchange",

            description=(
                "Create a size exchange request "
                "after the required information "
                "is known."
            ),

            parameters_json_schema={
                "type": "object",

                "properties": {

                    "order_id": {
                        "type": "string"
                    },

                    "sku": {
                        "type": "string"
                    },

                    "requested_size": {
                        "type": "string"
                    },
                },

                "required": [
                    "order_id",
                    "sku",
                    "requested_size",
                ],
            },
        ),

        types.FunctionDeclaration(
            name="escalate_to_human",

            description=(
                "Create a structured human-support "
                "handoff when the assistant cannot "
                "safely or completely resolve the issue."
            ),

            parameters_json_schema={
                "type": "object",

                "properties": {

                    "reason": {
                        "type": "string"
                    },

                    "customer_message": {
                        "type": "string"
                    },

                    "order_id": {
                        "type": "string"
                    },

                    "checks_performed": {
                        "type": "array",

                        "items": {
                            "type": "string"
                        },
                    },
                },

                "required": [
                    "reason",
                    "customer_message",
                ],
            },
        ),
    ]


# --------------------------------------------------
# Tool execution
# --------------------------------------------------

def execute_tool(
    name: str,
    arguments: dict[str, Any],
) -> Any:

    tools = {
        "lookup_order": lookup_order,
        "search_policy": search_policy,
        "check_return_eligibility": check_return_eligibility,
        "create_return": create_return,
        "create_exchange": create_exchange,
        "escalate_to_human": escalate_to_human,
    }

    if name not in tools:
        return {
            "error": f"Unknown tool: {name}"
        }

    result = tools[name](**arguments)

    

    return result

# --------------------------------------------------
# Main agent
# --------------------------------------------------

def chat(
    conversation_id: str,
    message: str,
    customer_id: str | None = None,
) -> str:

    state = get_state(conversation_id)

    if customer_id:
        state.customer_id = customer_id

    client = get_client()

    # Build conversation history
    contents = []

    for turn in state.history:
        contents.append(
            types.Content(
                role=turn["role"],
                parts=[
                    types.Part.from_text(
                        text=turn["text"]
                    )
                ],
            )
        )

    # Add previous order context
    context_parts = []

    if state.current_order_id:
        context_parts.append(
            f"Known order from earlier in this conversation: "
            f"{state.current_order_id}"
        )

    if state.current_sku:
        context_parts.append(
            f"Known item SKU from earlier in this conversation: "
            f"{state.current_sku}"
        )

    if state.pending_action:
        context_parts.append(
            f"Pending customer action: "
            f"{state.pending_action}"
        )

    context_parts.append(
        f"Customer message: {message}"
    )

    context_message = "\n".join(context_parts)

    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=context_message
                )
            ],
        )
    )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[
            types.Tool(
                function_declarations=get_tool_declarations()
            )
        ],
    )

    # Agentic tool-calling loop
    for _ in range(8):

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )
        

        candidate = response.candidates[0]
        parts = candidate.content.parts

        function_calls = [
            part.function_call
            for part in parts
            if part.function_call
        ]

        # No tool call -> final answer
        if not function_calls:

            answer = (
                response.text
                or "I couldn't generate a response."
            )

            state.history.append({
                "role": "user",
                "text": message,
            })

            state.history.append({
                "role": "model",
                "text": answer,
            })

            return answer

        # Add Gemini's tool request
        contents.append(candidate.content)

               # Execute requested tools
        for call in function_calls:

            tool_name = call.name

            arguments = dict(
                call.args or {}
            )

            result = None

            # ------------------------------------------
            # create_return safety checks
            # ------------------------------------------

            if tool_name == "create_return":

                requested_order = (
                    arguments.get(
                        "order_id",
                        ""
                    ).upper()
                )

                requested_sku = arguments.get(
                    "sku",
                    ""
                )

                if not state.current_order_id:

                    result = {
                        "success": False,
                        "reason": (
                            "No order has been established."
                        ),
                    }

                elif requested_order != state.current_order_id:

                    result = {
                        "success": False,
                        "reason": (
                            "The requested order does not "
                            "match the conversation context."
                        ),
                    }

                elif (
                    state.current_sku
                    and requested_sku != state.current_sku
                ):

                    result = {
                        "success": False,
                        "reason": (
                            "The requested item does not "
                            "match the conversation context."
                        ),
                    }

                elif not state.eligibility_checked:

                    result = {
                        "success": False,
                        "reason": (
                            "Return eligibility must be "
                            "checked first."
                        ),
                    }

                elif not state.return_eligible:

                    result = {
                        "success": False,
                        "reason": (
                            "The item is not eligible "
                            "for return."
                        ),
                    }

                elif not state.return_confirmation_required:

                    result = {
                        "success": False,
                        "reason": (
                            "Explicit customer confirmation "
                            "is required before creating "
                            "the return."
                        ),
                    }

                else:

                    result = execute_tool(
                        tool_name,
                        arguments,
                    )

                    state.return_confirmation_required = False

            else:

                # ------------------------------------------
                # Use conversation state for eligibility
                # ------------------------------------------

                if tool_name == "check_return_eligibility":

                    if state.current_order_id:
                        arguments["order_id"] = (
                            state.current_order_id
                        )

                    if state.current_sku:
                        arguments["sku"] = (
                            state.current_sku
                        )

                    if state.item_condition:
                        arguments["condition"] = (
                            state.item_condition
                        )

                    if state.has_original_tags is not None:
                        arguments["has_original_tags"] = (
                            state.has_original_tags
                        )

                    if state.has_original_packaging is not None:
                        arguments["has_original_packaging"] = (
                            state.has_original_packaging
                        )

                # ------------------------------------------
                # Execute normal tool
                # ------------------------------------------

                result = execute_tool(
                    tool_name,
                    arguments,
                )

            # ------------------------------------------
            # Update conversation state
            # ------------------------------------------

            if tool_name == "lookup_order":

                order = result

                # Customer ownership protection
                if (
                    isinstance(order, dict)
                    and state.customer_id
                    and order.get("customer_id")
                    != state.customer_id
                ):

                    result = {
                        "found": False,
                        "reason": (
                            "I can't provide information "
                            "about that order."
                        ),
                    }

                elif isinstance(order, dict):

                    order_id = order.get("order_id")

                    if order_id:
                        state.current_order_id = (
                            order_id.upper()
                        )

                    if (
                        order.get("items")
                        and len(order["items"]) == 1
                    ):

                        state.current_sku = (
                            order["items"][0]["sku"]
                        )

            # ------------------------------------------
            # Store return eligibility result
            # ------------------------------------------

            if tool_name == "check_return_eligibility":

                state.eligibility_checked = True

                state.return_eligible = bool(
                    isinstance(result, dict)
                    and result.get("eligible", False)
                )

                if state.return_eligible:
                    state.return_confirmation_required = True

            # ------------------------------------------
            # Send THIS tool result back to Gemini
            # ------------------------------------------

            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=tool_name,
                            response={
                                "result": result
                            },
                        )
                    ],
                )
            )

    raise RuntimeError(
        "Agent exceeded maximum tool-call steps."
    )