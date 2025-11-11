# Travel Agent

This project implements a LangGraph-powered corporate travel assistant that serves both WhatsApp group chats and a web chat channel. It showcases a strict booking flow with mocked Flights and Hotels APIs and provides a FastAPI server for handling inbound messages.

## Features

- LangGraph orchestration with dedicated nodes for parsing, searching, presenting, selecting, repricing/holding, confirming, booking, issuing, and finalizing itineraries.
- Hybrid NLU parser combining deterministic regex rules and an LLM-structured output abstraction.
- Mock Flights and Hotels tools with deterministic results suitable for tests and demos.
- Redis-ready services for idempotency, storage, and profile management (with in-memory fallbacks for local development).
- WhatsApp group webhook adapter with traveler permission checks and web chat adapter for authenticated users.
- Comprehensive tests covering parsing, the happy-path booking flow, permission guards, and hold expiry handling.

## Quickstart

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
```

Run the application:

```bash
uvicorn src.app:app --reload
```

Run the tests:

```bash
pytest -q
```

### Environment variables

Copy `.env.example` to `.env` and set the relevant variables:

- `OPENAI_API_KEY` – optional, required only when using the real OpenAI client.
- `REDIS_URL` – optional, defaults to in-memory stores when absent.

## Extending

Replace the mocked Flights/Hotels implementations in `src/tools` with real integrations by implementing the same Pydantic request/response models. The graph will continue to work as long as contracts remain intact.

