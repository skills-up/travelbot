from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

from .adapters.web import WebAdapter, WebChatPayload
from .adapters.whatsapp import WhatsAppAdapter, WhatsAppPayload
from .graph.build_graph import build_graph
from .graph.nodes import NodeContext
from .graph.state import ConversationState, make_conversation_state
from .nlu.parser import Parser
from .services.idempotency import IdempotencyService
from .services.profiles import ProfileService
from .services.storage import ConversationStorage
from .tools.flights import FlightsClient
from .tools.hotels import HotelsClient

app = FastAPI(title="Corporate Travel Agent")

redis_url = os.getenv("REDIS_URL")

profile_service = ProfileService()
parser = Parser()
flights_client = FlightsClient()
hotels_client = HotelsClient()
idempotency_service = IdempotencyService(redis_url=redis_url)
node_context = NodeContext(
    parser=parser,
    flights=flights_client,
    hotels=hotels_client,
    idempotency=idempotency_service,
)
compiled_graph = build_graph(node_context)
storage = ConversationStorage(redis_url=redis_url)

def _invoke_graph(state: ConversationState) -> ConversationState:
    result = compiled_graph.invoke(state)
    if isinstance(result, ConversationState):
        return result
    return ConversationState(**result)


def orchestrator(
    *,
    channel: str,
    conversation_id: str,
    user_id: str,
    text: str,
    sender_is_traveler: bool,
    group_id: str | None,
) -> str:
    stored = storage.load(conversation_id)
    profile = profile_service.get(user_id)
    if stored:
        state = ConversationState(**stored)
        state = state.model_copy(update={"profile": profile})
    else:
        state = make_conversation_state(channel=channel, user_id=user_id, profile=profile, group_id=group_id)
    state = state.model_copy(
        update={
            "last_message_text": text,
            "sender_is_traveler": sender_is_traveler,
            "group_id": group_id,
            "channel": channel,
        }
    )
    result_state = _invoke_graph(state)
    storage.save(conversation_id, result_state.model_dump(mode="json"))
    return result_state.last_outbound_text or "Noted."


whatsapp_adapter = WhatsAppAdapter(
    orchestrator=orchestrator,
    group_mapping={"demo-group": {"user_id": "user-1", "phone": "+910000000000"}},
)
web_adapter = WebAdapter(orchestrator=orchestrator)


class ResponsePayload(BaseModel):
    reply: str


@app.post("/whatsapp/webhook", response_model=ResponsePayload)
async def whatsapp_webhook(payload: WhatsAppPayload):
    reply = whatsapp_adapter.handle_message(payload)
    return ResponsePayload(reply=reply)


@app.post("/web/chat", response_model=ResponsePayload)
async def web_chat(payload: WebChatPayload):
    reply = web_adapter.handle_message(payload)
    return ResponsePayload(reply=reply)
