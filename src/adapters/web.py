from __future__ import annotations

from pydantic import BaseModel


class WebChatPayload(BaseModel):
    user_id: str
    conversation_id: str
    text: str


class WebAdapter:
    def __init__(self, orchestrator) -> None:
        self._orchestrator = orchestrator

    def handle_message(self, payload: WebChatPayload) -> str:
        return self._orchestrator(
            channel="web",
            conversation_id=payload.conversation_id,
            user_id=payload.user_id,
            text=payload.text,
            sender_is_traveler=True,
            group_id=None,
        )
