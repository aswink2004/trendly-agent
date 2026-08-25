# Trendly Agentic Support Assistant

An agentic customer-support assistant built for the Trendly FDE assessment.

The goal is to handle common customer-support requests such as order tracking, policy questions, returns, and exchanges while safely handing off cases that require human support.

The key design choice is that the LLM is not trusted to make business-critical decisions on its own. Gemini handles natural-language understanding and tool orchestration, while Python tools and application state enforce business rules and protect side-effecting actions.

---

## 1. Project Overview

The assistant combines Gemini's natural-language understanding with deterministic Python tools to provide a safe, multi-turn customer-support workflow.

The system is designed around three principles:

- The LLM handles intent understanding and tool selection.
- Python handles business-critical decisions.
- Side-effecting actions are protected by application-level guardrails.

This allows the assistant to remain flexible in conversation without allowing the LLM to directly make or authorize sensitive business decisions.

---

## 2. What the Agent Can Do

The assistant currently supports:

- Order status and delivery lookups
- Shipping and returns policy questions
- Return eligibility checks
- Multi-turn return conversations
- Return creation after explicit customer confirmation
- Exchange workflows
- Lost-parcel escalation
- Human support escalation
- Customer/order ownership protection
- Refusal of unsupported discounts and policy claims

---

## 3. Architecture

```text
                         Customer
                            |
                            v
                       FastAPI /chat
                            |
                            v
                       Gemini Agent
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
        lookup_order   search_policy   return tools
              |             |             |
              v             v             v
        orders.json    policy.md     Python rules
                                      and state
                                            |
                            +---------------+---------------+
                            |                               |
                            v                               v
                     create_return                  human escalation
                     create_exchange
```

Gemini is responsible for understanding the customer's request and deciding which tool should be called.

Python is responsible for:

- Business rules
- Eligibility decisions
- Conversation state
- Customer/order authorization
- Side-effect protection

The agent uses native Gemini function calling rather than keyword-based routing.

---

## 4. Return Workflow

A typical return conversation works as follows:

```text
Customer:
"What is the status of TR-4530?"
        |
        v
lookup_order
        |
        v
Order TR-4530 → Delivered
Item → Block-Print Kurta
SKU → TR-KRT-033
        |
        v
Customer:
"Can I return it?"
        |
        v
Agent asks for item condition
        |
        v
Customer:
"It is unworn and unwashed, tags are attached,
and I have the original packaging."
        |
        v
check_return_eligibility
        |
        v
Eligible
        |
        v
Agent asks for explicit confirmation
        |
        v
Customer:
"Yes, please proceed."
        |
        v
Application safety checks
        |
        v
create_return()
```

The LLM does not directly decide whether the return should be created.

Before `create_return()` is allowed, the application verifies the order, SKU, eligibility result, conversation state, and explicit customer confirmation.

---

## 5. Tools

The agent uses native Gemini function calling to interact with deterministic application tools.

| Tool                         | Purpose                                                             |
|------------------------------|---------------------------------------------------------------------|
| `lookup_order`               | Retrieves order information and supports customer ownership checks. |
| `search_policy`              | Retrieves relevant information from the Trendly policy.             |
| `check_return_eligibility`   | Deterministically evaluates return eligibility.                     |
| `create_return`              | Creates a return only after required safety checks pass.            |
| `create_exchange`            | Handles supported exchange requests.                                |
| `escalate_to_human`          | Escalates cases requiring human support.                            |

Business-critical decisions are enforced by Python rather than delegated entirely to the LLM.

---

## 6. Safety & Guardrails

Safety-sensitive behavior is enforced in application code rather than relying only on prompt instructions.

### Customer Isolation

The application verifies that the customer is authorized to access the requested order.

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
Do not disclose order information
```

A customer must match the order's customer identity before order information can be returned.

### Return Protection

A return cannot be created unless:

1. The order is known.
2. The customer is authorized to access the order.
3. The requested SKU matches the conversation context.
4. Return eligibility has been checked.
5. The item is actually eligible.
6. The customer has explicitly confirmed the return.

### Lost Parcels

Lost parcels are not processed as normal returns.

They are escalated to human support according to the Trendly policy.

### Unsupported Discounts

There is no discount or goodwill-credit tool.

Unsupported discounts are therefore refused rather than being invented or created by the model.

### Sensitive Information

The assistant must not collect sensitive payment information such as:

- Card numbers
- CVV
- Bank account numbers

Cases requiring sensitive information are handled through the appropriate human-support workflow.

---

## 7. Policy Grounding

The source of truth for Trendly policy questions is:

```text
data/trendly_policy.md
```

The assistant uses `search_policy` to retrieve relevant policy information instead of relying on general model knowledge.

The policy covers areas including:

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

If the policy does not cover a question, the assistant should not invent an answer and should offer human support.

---

## 8. Conversation State

The application maintains state for multi-turn conversations.

Relevant state includes:

- Customer ID
- Current order ID
- Current SKU
- Item condition
- Original tags
- Original packaging
- Eligibility status
- Return confirmation status
- Conversation history

For example:

```text
Turn 1:
"What is the status of TR-4530?"

State:
current_order_id = TR-4530
current_sku = TR-KRT-033

Turn 2:
"Can I return it?"

Agent:
Requests condition information.

Turn 3:
"It is unworn and unwashed, tags attached,
and I have the original packaging."

State:
Return facts are stored.

Turn 4:
"Yes, please proceed."

Application:
Checks eligibility and confirmation
before allowing create_return().
```

This prevents the customer from having to repeat information across turns and allows the application to enforce state-dependent safety checks.

---

## 9. Running Locally

### Install dependencies

```bash
pip install -r requirements.txt
```

The project uses:

```text
fastapi
uvicorn[standard]
google-genai
python-dotenv
pydantic
pytest
httpx
```

### Configure environment variables

Create a local `.env` file:

```text
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
```

Do not commit `.env` or real API keys to the repository.

A safe template is provided in:

```text
.env.example
```

### Start the application

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 10. Testing

The project includes tests for the deterministic business logic and agent state.

Run the test suite with:

```bash
python -m pytest
```

The tests cover scenarios including:

- Known and unknown orders
- Shipping policy retrieval
- Lost-parcel policy
- Successful return eligibility
- Expired return windows
- Non-returnable categories
- Final-sale items
- Cancelled orders
- Lost parcels
- Missing original tags
- Footwear packaging requirements
- Human escalation
- Multi-turn return state
- Customer isolation

Syntax can also be checked with:

```bash
python -m py_compile app\agent.py app\state.py app\main.py
```

The deterministic business logic is tested separately from LLM calls so core rules can be verified without consuming API quota.

---

## 11. Project Structure

```text
                                trendly-agent/
                                │
                                ├── app/
                                │   ├── agent.py
                                │   ├── main.py
                                │   ├── prompts.py
                                │   ├── state.py
                                │   │
                                │   ├── static/
                                │   │   └── index.html
                                │   │
                                │   └── tools/
                                │       ├── orders.py
                                │       ├── policy.py
                                │       ├── returns.py
                                │       ├── escalation.py
                                │       └── __init__.py
                                │
                                ├── data/
                                │   ├── orders.json
                                │   └── trendly_policy.md
                                │
                                ├── tests/
                                │   ├── test_tools.py
                                │   └── test_agent.py
                                │
                                ├── .env.example
                                ├── .gitignore
                                ├── requirements.txt
                                ├── README.md
                                ├── prompts.md
                                └── SOLUTION.md
```
# Trendly Agentic Support Assistant

An agentic customer-support assistant built for the Trendly FDE assessment.

The goal is to handle common customer-support requests such as order tracking, policy questions, returns, and exchanges while safely handing off cases that require human support.

The key design choice is that the LLM is not trusted to make business-critical decisions on its own. Gemini handles natural-language understanding and tool orchestration, while Python tools and application state enforce business rules and protect side-effecting actions.

---

## 1. Project Overview

The assistant combines Gemini's natural-language understanding with deterministic Python tools to provide a safe, multi-turn customer-support workflow.

The system is designed around three principles:

- The LLM handles intent understanding and tool selection.
- Python handles business-critical decisions.
- Side-effecting actions are protected by application-level guardrails.

This allows the assistant to remain flexible in conversation without allowing the LLM to directly make or authorize sensitive business decisions.

---

## 2. What the Agent Can Do

The assistant currently supports:

- Order status and delivery lookups
- Shipping and returns policy questions
- Return eligibility checks
- Multi-turn return conversations
- Return creation after explicit customer confirmation
- Exchange workflows
- Lost-parcel escalation
- Human support escalation
- Customer/order ownership protection
- Refusal of unsupported discounts and policy claims

---

## 3. Architecture

```text
                         Customer
                            |
                            v
                       FastAPI /chat
                            |
                            v
                       Gemini Agent
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
        lookup_order   search_policy   return tools
              |             |             |
              v             v             v
        orders.json    policy.md     Python rules
                                      and state
                                            |
                            +---------------+---------------+
                            |                               |
                            v                               v
                     create_return                  human escalation
                     create_exchange
```

Gemini is responsible for understanding the customer's request and deciding which tool should be called.

Python is responsible for:

- Business rules
- Eligibility decisions
- Conversation state
- Customer/order authorization
- Side-effect protection

The agent uses native Gemini function calling rather than keyword-based routing.

---

## 4. Return Workflow

A typical return conversation works as follows:

```text
Customer:
"What is the status of TR-4530?"
        |
        v
lookup_order
        |
        v
Order TR-4530 → Delivered
Item → Block-Print Kurta
SKU → TR-KRT-033
        |
        v
Customer:
"Can I return it?"
        |
        v
Agent asks for item condition
        |
        v
Customer:
"It is unworn and unwashed, tags are attached,
and I have the original packaging."
        |
        v
check_return_eligibility
        |
        v
Eligible
        |
        v
Agent asks for explicit confirmation
        |
        v
Customer:
"Yes, please proceed."
        |
        v
Application safety checks
        |
        v
create_return()
```

The LLM does not directly decide whether the return should be created.

Before `create_return()` is allowed, the application verifies the order, SKU, eligibility result, conversation state, and explicit customer confirmation.

---

## 5. Tools

The agent uses native Gemini function calling to interact with deterministic application tools.

| Tool                         | Purpose                                                             |
|------------------------------|---------------------------------------------------------------------|
| `lookup_order`               | Retrieves order information and supports customer ownership checks. |
| `search_policy`              | Retrieves relevant information from the Trendly policy.             |
| `check_return_eligibility`   | Deterministically evaluates return eligibility.                     |
| `create_return`              | Creates a return only after required safety checks pass.            |
| `create_exchange`            | Handles supported exchange requests.                                |
| `escalate_to_human`          | Escalates cases requiring human support.                            |

Business-critical decisions are enforced by Python rather than delegated entirely to the LLM.

---

## 6. Safety & Guardrails

Safety-sensitive behavior is enforced in application code rather than relying only on prompt instructions.

### Customer Isolation

The application verifies that the customer is authorized to access the requested order.

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
Do not disclose order information
```

A customer must match the order's customer identity before order information can be returned.

### Return Protection

A return cannot be created unless:

1. The order is known.
2. The customer is authorized to access the order.
3. The requested SKU matches the conversation context.
4. Return eligibility has been checked.
5. The item is actually eligible.
6. The customer has explicitly confirmed the return.

### Lost Parcels

Lost parcels are not processed as normal returns.

They are escalated to human support according to the Trendly policy.

### Unsupported Discounts

There is no discount or goodwill-credit tool.

Unsupported discounts are therefore refused rather than being invented or created by the model.

### Sensitive Information

The assistant must not collect sensitive payment information such as:

- Card numbers
- CVV
- Bank account numbers

Cases requiring sensitive information are handled through the appropriate human-support workflow.

---

## 7. Policy Grounding

The source of truth for Trendly policy questions is:

```text
data/trendly_policy.md
```

The assistant uses `search_policy` to retrieve relevant policy information instead of relying on general model knowledge.

The policy covers areas including:

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

If the policy does not cover a question, the assistant should not invent an answer and should offer human support.

---

## 8. Conversation State

The application maintains state for multi-turn conversations.

Relevant state includes:

- Customer ID
- Current order ID
- Current SKU
- Item condition
- Original tags
- Original packaging
- Eligibility status
- Return confirmation status
- Conversation history

For example:

```text
Turn 1:
"What is the status of TR-4530?"

State:
current_order_id = TR-4530
current_sku = TR-KRT-033

Turn 2:
"Can I return it?"

Agent:
Requests condition information.

Turn 3:
"It is unworn and unwashed, tags attached,
and I have the original packaging."

State:
Return facts are stored.

Turn 4:
"Yes, please proceed."

Application:
Checks eligibility and confirmation
before allowing create_return().
```

This prevents the customer from having to repeat information across turns and allows the application to enforce state-dependent safety checks.

---

## 9. Running Locally

### Install dependencies

```bash
pip install -r requirements.txt
```

The project uses:

```text
fastapi
uvicorn[standard]
google-genai
python-dotenv
pydantic
pytest
httpx
```

### Configure environment variables

Create a local `.env` file:

```text
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
```

Do not commit `.env` or real API keys to the repository.

A safe template is provided in:

```text
.env.example
```

### Start the application

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 10. Testing

The project includes tests for the deterministic business logic and agent state.

Run the test suite with:

```bash
python -m pytest
```

The tests cover scenarios including:

- Known and unknown orders
- Shipping policy retrieval
- Lost-parcel policy
- Successful return eligibility
- Expired return windows
- Non-returnable categories
- Final-sale items
- Cancelled orders
- Lost parcels
- Missing original tags
- Footwear packaging requirements
- Human escalation
- Multi-turn return state
- Customer isolation

Syntax can also be checked with:

```bash
python -m py_compile app\agent.py app\state.py app\main.py
```

The deterministic business logic is tested separately from LLM calls so core rules can be verified without consuming API quota.

---

## 11. Project Structure

```text
                                trendly-agent/
                                │
                                ├── app/
                                │   ├── agent.py
                                │   ├── main.py
                                │   ├── prompts.py
                                │   ├── state.py
                                │   │
                                │   ├── static/
                                │   │   └── index.html
                                │   │
                                │   └── tools/
                                │       ├── orders.py
                                │       ├── policy.py
                                │       ├── returns.py
                                │       ├── escalation.py
                                │       └── __init__.py
                                │
                                ├── data/
                                │   ├── orders.json
                                │   └── trendly_policy.md
                                │
                                ├── tests/
                                │   ├── test_tools.py
                                │   └── test_agent.py
                                │
                                ├── .env.example
                                ├── .gitignore
                                ├── requirements.txt
                                ├── README.md
                                ├── prompts.md
                                └── SOLUTION.md
```
## AI Usage Note

AI tools, including ChatGPT, were used during development to assist with code generation, debugging, prompt refinement, documentation, test-case design, and reviewing implementation approaches.

AI assistance was primarily used as a development aid. The final architecture, tool definitions, conversation-state design, business-rule guardrails, customer-isolation checks, return workflow, and error-handling logic were reviewed, tested, and modified as part of the implementation.

At runtime, Gemini is used for natural-language understanding, response generation, and native function calling. The LLM is not trusted to make business-critical decisions independently. Order authorization, return eligibility, confirmation requirements, and side-effecting actions such as return creation are enforced through deterministic Python application logic.

The implementation was tested locally using the automated test suite, with all 16 tests passing. The AI-generated suggestions were therefore validated against the application's requirements and modified where necessary rather than being used blindly.