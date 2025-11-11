from __future__ import annotations

from typing import Dict

from fastapi import HTTPException
from pydantic import BaseModel


class WhatsAppPayload(BaseModel):
    group_id: str
    sender_phone: str
    text: str


class WhatsAppAdapter:
    def __init__(
        self,
        orchestrator,
        group_mapping: Dict[str, Dict[str, str]],
    ) -> None:
        self._orchestrator = orchestrator
        self._group_mapping = group_mapping

    def handle_message(self, payload: WhatsAppPayload) -> str:
        mapping = self._group_mapping.get(payload.group_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="Unknown group")
        user_id = mapping["user_id"]
        sender_is_traveler = payload.sender_phone == mapping.get("phone")
        response = self._orchestrator(
            channel="whatsapp_group",
            conversation_id=payload.group_id,
            user_id=user_id,
            text=payload.text,
            sender_is_traveler=sender_is_traveler,
            group_id=payload.group_id,
        )
        return response

    def register_group(self, group_id: str, user_id: str, phone: str) -> None:
        self._group_mapping[group_id] = {"user_id": user_id, "phone": phone}
