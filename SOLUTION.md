# Solution — Trendly Agentic Support Assistant

## 1. Overview

The Trendly Support Assistant is an agentic customer-support system designed to handle repetitive support requests while keeping business-critical decisions deterministic and safe.

The system uses Gemini for natural-language understanding and native function calling. Python tools are responsible for retrieving data, applying business rules, maintaining conversation state, enforcing authorization, and protecting side-effecting operations.

The main design principle is:

> **Use the LLM for understanding and orchestration; use deterministic code for business rules and side effects.**

This prevents the model from independently deciding whether a sensitive action such as creating a return should be performed.

---

## 2. High-Level Architecture

```text
                         Customer
                            |
                            v
                       FastAPI API
                            |
                            v
                      Agent / Gemini
                            |
                 Native Function Calling
                            |
             +--------------+--------------+
             |              |              |
             v              v              v
        lookup_order   search_policy   return/exchange
             |              |              |
             v              v              v
        orders.json    policy.md       Python rules
                                           |
                              +------------+------------+
                              |                         |
                              v                         v
                       Side-effect tools          Human escalation
```

The architecture separates language understanding from business logic.

Gemini can determine that a customer is asking about a return and request the appropriate tool. The application then validates the requested operation before allowing any side effect.

---

## 3. Agentic Tool-Calling Loop

The assistant uses native Gemini function calling rather than keyword matching.

The general loop is:

```text
1. Customer sends a message
          |
          v
2. Gemini receives conversation + tool schemas
          |
          v
3. Gemini decides whether a tool is required
          |
          v
4. Application executes the requested tool
          |
          v
5. Tool result is added back to the conversation
          |
          v
6. Gemini processes the result
          |
          v
7. Gemini either requests another tool
   or produces the final response
```

This allows multiple tools to be combined within a single user workflow.

For example, a return request can require:

```text
lookup_order
      ↓
check_return_eligibility
      ↓
explicit customer confirmation
      ↓
create_return
```

The model orchestrates the sequence, while application code controls whether each operation is actually allowed.

---

## 4. Tool Layer

The application exposes deterministic tools to the agent.

### `lookup_order`

Retrieves order information from the local order dataset.

The result contains information such as:

- Order ID
- Customer ID
- Order status
- Delivery information
- Carrier
- Tracking number
- Items
- SKU
- Price
- Final-sale status

The application uses the customer identity to prevent an authenticated customer from accessing another customer's order.

### `search_policy`

Retrieves relevant sections from:

```text
data/trendly_policy.md
```

The policy file is treated as the source of truth for Trendly policy questions.

The model should use retrieved policy information rather than relying on unsupported assumptions.

### `check_return_eligibility`

Return eligibility is calculated deterministically in Python.

The tool evaluates the supplied order and item information against the return rules, including:

- Delivery date
- Return window
- Order status
- Product category
- Final-sale status
- Item condition
- Original tags
- Original packaging
- Footwear requirements

This is deliberately not delegated to the LLM.

### `create_return`

This is a side-effecting operation and is therefore protected by application-level checks.

The tool should only execute after the required conditions have been established.

### `create_exchange`

Handles supported exchange workflows according to the supplied business rules.

### `escalate_to_human`

Handles situations where the assistant should not continue autonomously, such as lost-parcel cases or questions that are not covered by the supplied policy.

---

## 5. Deterministic Return Eligibility

A key architectural decision is separating eligibility calculation from language generation.

The LLM may understand:

> "The item is unworn, the tags are attached, and I still have the packaging."

However, the LLM should not be trusted to convert that statement into the final business decision.

Instead:

```text
Customer facts
      |
      v
Application state
      |
      v
check_return_eligibility()
      |
      v
Deterministic result
      |
      +---- eligible
      |
      +---- not_eligible
      |
      +---- human / special handling
```

This makes the business decision reproducible and testable.

---

## 6. Side-Effect Protection

Creating a return is treated differently from simply answering a question.

Before `create_return` is allowed, the application verifies:

1. An order has been established.
2. The requested order matches the current conversation order.
3. The requested SKU matches the current conversation item.
4. Return eligibility has already been checked.
5. The eligibility result is positive.
6. The customer has explicitly confirmed that they want to proceed.

This creates a separation between:

```text
"Can I return this?"
```

and:

```text
"Yes, please proceed."
```

The first request should result in an eligibility workflow.

The second request is required before the side effect is performed.

This reduces the risk of accidental returns caused by ambiguous language.

---

## 7. Customer Isolation

Order information is customer-specific.

The application therefore checks the customer associated with the order before exposing order details.

Example:

```text
Customer C-999
      |
      v
Requests TR-4530
      |
      v
TR-4530 belongs to C-101
      |
      v
Access denied
```

For the correct customer:

```text
Customer C-101
      |
      v
Requests TR-4530
      |
      v
Ownership verified
      |
      v
Order information returned
```

This check is implemented at the application/tool layer rather than relying only on the model to follow a prompt instruction.

---

## 8. Policy Grounding

The supplied policy document is:

```text
data/trendly_policy.md
```

It is treated as the authoritative source for policy questions.

The policy includes rules for:

- Shipping
- Delivery estimates
- Shipping charges
- Delayed orders
- Lost parcels
- Address changes
- Returns
- Return windows
- Non-returnable categories
- Final-sale items
- Footwear
- Refunds
- Exchanges
- Return pickup
- Damaged or incorrect items

The assistant should not invent policy when the document is silent.

If a question is not covered, the expected behavior is to explain that the policy does not provide the requested information and offer human support.

---

## 9. Conversation State

The application maintains state for each conversation.

Important state fields include:

```text
customer_id
current_order_id
current_sku
item_condition
has_original_tags
has_original_packaging
eligibility_checked
return_eligible
return_confirmation_required
history
```

This state allows information to be accumulated across multiple turns.

For example:

```text
Turn 1:
"What is the status of TR-4530?"

State:
current_order_id = TR-4530
current_sku = TR-KRT-033

Turn 2:
"Can I return it?"

Agent asks for condition information.

Turn 3:
"It is unworn and unwashed, tags attached,
and I have the original packaging."

State:
return facts are stored.

Turn 4:
"Yes, please proceed."

Application:
eligibility and confirmation are verified.
```

This is important because customer support workflows are rarely completed in one message.

---

## 10. Lost Parcel Handling

Lost parcels are intentionally separated from ordinary returns.

The supplied Trendly policy states that a lost parcel is a lost-parcel claim rather than a return and must be handled by human support.

The workflow is therefore:

```text
Order lookup
     |
     v
Parcel marked lost
     |
     v
Do not create return
     |
     v
escalate_to_human()
```

This prevents the assistant from applying an incorrect return workflow to a fundamentally different support case.

---

## 11. Unsupported Requests

The system deliberately does not provide a tool for unsupported discounts or goodwill credits.

This is an important safety design choice.

Instead of giving the model a discount tool and attempting to control when it is used, the tool simply does not exist.

Therefore:

```text
Customer:
"Give me a 50% discount."

        ↓

No discount tool exists

        ↓

Assistant refuses according to policy
or offers human support
```

This follows the principle of minimizing unnecessary capabilities.

---

## 12. Testing Strategy

The business logic is tested independently from live LLM calls.

This is important because LLM responses are probabilistic and API usage may be rate-limited or unavailable.

The deterministic tests cover cases including:

- Known order
- Unknown order
- Return window
- Expired return
- Non-returnable category
- Final-sale item
- Cancelled order
- Lost parcel
- Missing tags
- Footwear packaging
- Human escalation
- Return eligibility

The agent-level tests also exercise conversation state and safety-related behavior.

Typical commands:

```bash
python -m pytest
```

and:

```bash
python -m py_compile app/agent.py app\state.py app\main.py
```

This separation allows the core business rules to be verified without spending LLM API quota.

---

## 13. Why Gemini?

Gemini was selected because the project requires natural-language understanding and native function calling.

The model is used primarily for:

- Understanding user intent
- Extracting structured tool arguments
- Selecting appropriate tools
- Interpreting tool results
- Producing the final natural-language response

The model is not treated as the source of truth for:

- Order data
- Policy data
- Return eligibility
- Customer authorization
- Side-effect authorization

Those responsibilities remain in application code.

---

## 14. Trade-offs

### In-memory state

The current implementation uses in-memory conversation state.

Advantages:

- Simple
- Fast
- No database dependency
- Easy to run for an assessment

Trade-off:

- State is lost when the application restarts.
- It is not suitable for multiple production instances without shared storage.

### Local deterministic data

Orders and policy are stored locally.

Advantages:

- Reproducible
- Easy to test
- No external database dependency
- No additional infrastructure

Trade-off:

- Not suitable for a production environment where order data changes dynamically.

### LLM orchestration

Using Gemini provides flexible natural-language interaction.

Trade-off:

- LLM calls can fail or hit quota limits.
- Tool argument generation must be validated.
- The application cannot rely on the model alone for business-critical decisions.

The architecture addresses this by keeping deterministic rules and side-effect guards outside the model.

---

## 15. Failure Handling

The system is designed to fail safely.

### Unknown order

```text
Unknown order
     |
     v
Do not invent order information
     |
     v
Ask for clarification or offer support
```

### Unknown policy

```text
Policy does not cover the question
     |
     v
Do not invent policy
     |
     v
Offer human support
```

### Unauthorized order

```text
Customer does not own order
     |
     v
Do not disclose order information
```

### Ineligible return

```text
Eligibility check
     |
     v
eligible = false
     |
     v
Do not create return
```

### Missing confirmation

```text
Eligibility = true
     |
     v
No explicit confirmation
     |
     v
Do not create return
```

These checks make the system fail closed for sensitive actions.

---

## 16. Production Considerations

If this assessment project were extended into a production system, the next improvements would include:

- Persistent conversation state
- Strong authentication and authorization
- Database-backed order and return records
- Structured audit logs
- Rate limiting
- LLM retry and backoff
- Monitoring and metrics
- Distributed session storage
- Role-based access for support agents
- Stronger validation of tool arguments
- Production-grade secrets management

The current implementation intentionally avoids unnecessary infrastructure so the core agentic workflow can remain easy to run and evaluate.

---

## 17. Summary

The architecture is intentionally hybrid:

```text
                  Gemini
                     |
          Natural Language
          + Tool Orchestration
                     |
                     v
              Python Tools
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
     Data        Business       State
                  Rules
                     |
                     v
              Safety Guards
                     |
                     v
               Side Effects
```

The LLM provides the flexibility required for a conversational support assistant, while deterministic application logic provides the reliability required for business-critical operations.

The central design principle is:

> **The model can request an action, but the application decides whether that action is allowed.**
