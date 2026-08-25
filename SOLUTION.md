# Trendly Agent — Solution Note

## 1. Architecture

The Trendly Support Assistant is a multi-turn agent built with Python, FastAPI, and Gemini.

The customer interacts with the FastAPI frontend/API. Gemini handles natural-language understanding and decides which available tool should be used.

The application provides deterministic tools for:

- Order lookup
- Policy questions
- Return eligibility
- Return creation
- Exchange handling
- Human escalation

Conversation state stores the customer ID, current order, current SKU, return-condition facts, eligibility status, confirmation state, and conversation history.

The supplied `trendly_policy.md` is the only source of truth for policy questions, while order information is loaded from the supplied `orders.json`.

The main design principle is:

> **Use the LLM for language understanding and orchestration; use deterministic application code for business-critical rules, authorization, and side effects.**

## 2. Key Design Decisions and Trade-offs

### LLM orchestration, Python enforcement

Gemini is used for natural-language understanding and native tool calling. Business-critical decisions are implemented in Python so they are deterministic, testable, and easier to audit.

### Return safety

The return workflow is separated into identification, eligibility checking, explicit customer confirmation, and return creation.

`create_return()` is only allowed when the order and SKU match the conversation state, eligibility has been checked successfully, and the customer explicitly confirms the action.

### Customer isolation

Order ownership is checked at the application/tool layer rather than relying only on the LLM prompt. If an order belongs to another customer, its details are not exposed.

### Conversation state

Important workflow facts are stored explicitly in application state instead of relying only on the model's memory of previous messages. This supports multi-turn conversations and safer authorization.

### Local data

The assessment's fixed `orders.json` and `trendly_policy.md` are used directly to keep the implementation reproducible and easy to test. In production, these would be replaced by authenticated business systems and APIs.

## 3. Known Limitations

The current implementation is an assessment prototype rather than a production integration.

- `create_return()` is a mock action rather than a real OMS integration.
- Conversation state is held in application memory and is lost when the application restarts.
- Order data is static and limited to the supplied assessment dataset.
- The application depends on the availability and quota of the selected LLM provider.
- Production authentication, persistent storage, monitoring, audit logging, and external-service retry handling would still need to be added.

The automated test suite currently contains 16 tests covering order lookup, policy rules, returns, exchanges, escalation, conversation state, customer isolation, and edge cases. All 16 tests pass.

## 4. Safety and Policy Grounding

The assistant treats `trendly_policy.md` as the authoritative policy source and does not invent unsupported policies, discounts, waivers, refund timelines, or order information.

Return eligibility is determined by deterministic policy/tool logic rather than by the model's own reasoning.

Lost parcels are not processed as normal returns and are escalated to human support.

Side-effecting actions require explicit customer confirmation, and customer order data is protected by application-level ownership checks.

## 5. Discovery Questions for Trendly Ops

Before building this system for production, I would ask:

1. **What systems are the sources of truth for orders, shipments, refunds, inventory, and customer information, and what APIs are available?**

2. **How should the support agent authenticate and verify a customer before exposing order information or performing an action?**

3. **Which support actions are safe to automate, and which situations must always be reviewed by a human?**

4. **What should the escalation workflow look like, including the destination team, required information, and expected response SLA?**

5. **Which operational metrics should we track, such as automation rate, escalation rate, incorrect decisions, customer satisfaction, and tool/API failures?**

## 6. Summary

The design combines flexible natural-language interaction with deterministic business rules.

Gemini handles language understanding and tool orchestration, while the application enforces customer authorization, policy decisions, conversation state, and side-effect safety.

This separation provides a safer and more testable foundation for extending the assessment prototype into a production customer-support agent.