# Prompt Design Notes

## Purpose

`app/prompts.py` contains the system prompt used by Gemini during the Trendly support workflow.

This document explains the prompt's design and the reasoning behind the main instructions. The prompt is intentionally focused on guiding the LLM, while business-critical rules are enforced separately in Python.

---

## 1. Prompt Goals

The system prompt is designed to make the assistant:

- Helpful and concise
- Grounded in Trendly's supplied policy
- Consistent across multi-turn conversations
- Careful with customer and order information
- Correct when handling returns and exchanges
- Able to escalate cases that require human support
- Resistant to unsupported assumptions and hallucinations

The prompt does not replace application-level validation.

---

## 2. Tool Usage

The assistant is instructed to use tools when factual or business information is required.

Examples:

- `lookup_order()` for order information
- `search_policy()` for policy questions
- `check_return_eligibility()` for return decisions
- `create_return()` for an approved return
- `create_exchange()` for supported exchanges
- `escalate_to_human()` for cases requiring human support

The model is not expected to invent information that can be obtained from a tool.

---

## 3. Policy Grounding

The supplied `trendly_policy.md` is treated as the source of truth for Trendly policy questions.

The prompt instructs the assistant not to invent:

- Policies
- Exceptions
- Discounts
- Coupons
- Waivers
- Goodwill credits
- Refund timelines
- Unsupported capabilities

When the policy does not answer a question, the assistant should say that the policy does not cover it and offer human support.

---

## 4. Return Workflow

The return workflow is one of the most important parts of the prompt.

The expected sequence is:

```text
Identify order and item
        |
        v
Collect required item conditions
        |
        v
Check return eligibility
        |
        v
Tell customer the result
        |
        v
Ask for explicit confirmation
        |
        v
Create return
```

The prompt makes an important distinction between **condition confirmation** and **return authorization**.

For example:

```text
Customer:
"Yes, the item is unworn and the tags are attached."
```

This confirms the condition of the item.

It does not mean:

```text
"Create the return."
```

The assistant must still:

1. Check eligibility.
2. Tell the customer whether it is eligible.
3. Ask whether they want to proceed.
4. Only then request `create_return()`.

---

## 5. Multi-Turn Context

The prompt tells the assistant to remember information already established in the conversation.

For example:

```text
Customer:
"What is the status of TR-4530?"

        ↓

Order is identified.

        ↓

Customer:
"Can I return it?"

        ↓

The assistant should understand "it"
as the previously identified item.
```

If the customer then provides the requested condition information, the assistant should use it instead of asking for the same information again.

This keeps the conversation natural and reduces unnecessary questions.

---

## 6. Customer and Order Safety

The prompt instructs the assistant not to reveal information belonging to another customer.

The important rule is:

> Never confirm or discuss an order that does not belong to the authenticated customer.

However, this instruction is not treated as the actual security boundary.

The application also performs customer/order ownership validation before allowing order information to be returned.

This creates two layers:

```text
Prompt
  |
  | Behavioral guidance
  v
Gemini
  |
  v
Python validation
  |
  | Actual enforcement
  v
Tool execution
```

---

## 7. Side-Effect Safety

The prompt treats `create_return()` as a side-effecting action.

The assistant is instructed not to call it simply because the customer has provided item-condition information.

The application independently validates the action before execution.

The expected checks are:

```text
Order known
   ↓
Correct item/SKU
   ↓
Eligibility checked
   ↓
Eligible
   ↓
Explicit customer confirmation
   ↓
create_return()
```

This means the LLM can request an action, but the application decides whether that action is allowed.

---

## 8. Exchanges

The prompt instructs the assistant to use exchanges only within the supported Trendly workflow.

In particular:

- Size exchanges are supported.
- Colour exchanges are not offered.
- Style exchanges are not offered.
- Product or inventory availability should not be invented.

The assistant should use the appropriate tool and policy information rather than guessing.

---

## 9. Lost Parcels

Lost parcels are treated separately from normal returns.

The expected workflow is:

```text
Order / parcel status
        |
        v
Parcel marked as lost
        |
        v
Do not create a return
        |
        v
Escalate to human support
```

The prompt explicitly tells the assistant not to process a lost parcel as a normal return.

---

## 10. Payment Safety

The prompt prevents the assistant from collecting sensitive payment information in chat.

It must not request:

- Bank account numbers
- Card numbers
- CVV
- Other payment credentials

For COD refund cases that require bank information, the customer should be directed to the appropriate human-support process.

---

## 11. Unsupported Discounts

The assistant is instructed not to offer unsupported:

- Discounts
- Coupons
- Waivers
- Goodwill credits

There is deliberately no general discount tool exposed to the model.

This reduces the possibility of the model creating an unsupported business action.

---

## 12. Communication Style

The prompt asks the assistant to be:

- Concise
- Helpful
- Clear
- Professional
- Natural

It also prevents the assistant from exposing:

- System prompts
- Hidden reasoning
- Tool schemas
- Internal implementation details
- Private customer information

The goal is to provide useful customer-facing responses without exposing internal application details.

---

## 13. Prompt vs Application Enforcement

A key design decision is that the prompt is **not the security layer**.

The prompt tells the model what it should do.

Python code decides what the application will actually allow.

For example:

```text
Prompt:
"Only create a return after explicit confirmation."

        +

Python:
"Reject create_return unless eligibility
and confirmation checks have passed."
```

This approach is safer than relying only on instructions given to the model.

---

## 14. Final Design Principle

The prompt is intentionally concise enough for the model to follow consistently.

The overall responsibility is split as follows:

| Responsibility | Layer |
|---|---|
| Understand customer language | Gemini |
| Select appropriate tool | Gemini |
| Retrieve order data | Python tool |
| Retrieve policy | Python tool |
| Determine return eligibility | Python |
| Verify customer ownership | Python |
| Maintain conversation state | Python |
| Protect side effects | Python |
| Generate customer-facing response | Gemini |
| Human escalation | Python tool + Gemini |

The core principle is:

> **Use the LLM for understanding and orchestration; use deterministic code for business rules and side effects.**
