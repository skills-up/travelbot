from datetime import timedelta

from src import app
from src.adapters.whatsapp import WhatsAppPayload
from src.graph.state import ConversationState
from src.services import timeutil


def reset_storage():
    if hasattr(app.storage, "_memory"):
        app.storage._memory.clear()


def load_state(conversation_id: str) -> ConversationState:
    stored = app.storage.load(conversation_id)
    assert stored is not None
    return ConversationState(**stored)


def test_happy_path_booking_flow():
    reset_storage()
    conversation_id = "group-123"
    app.whatsapp_adapter.register_group(conversation_id, "user-123", "+911234567890")

    message = WhatsAppPayload(group_id=conversation_id, sender_phone="+911234567890", text="Hi, need Mum-Del on Nov 11th 3pm-5pm and hotel Aerocity Nov 12-13")
    reply = app.whatsapp_adapter.handle_message(message)
    assert "Flights" in reply
    assert "Hotels" in reply

    select_msg = WhatsAppPayload(group_id=conversation_id, sender_phone="+911234567890", text="F2 H2")
    confirm_prompt = app.whatsapp_adapter.handle_message(select_msg)
    assert "CONFIRM" in confirm_prompt

    confirm_msg = WhatsAppPayload(group_id=conversation_id, sender_phone="+911234567890", text="CONFIRM F2 H2")
    final_reply = app.whatsapp_adapter.handle_message(confirm_msg)
    assert "Booking complete" in final_reply
    state = load_state(conversation_id)
    assert state.itinerary.pnr == "PNR123"
    assert state.itinerary.hotel_conf == "HOTEL-12345"
    assert state.itinerary.ticket_numbers


def test_non_traveler_cannot_confirm():
    reset_storage()
    conversation_id = "group-456"
    app.whatsapp_adapter.register_group(conversation_id, "user-456", "+919999999999")

    app.orchestrator(
        channel="whatsapp_group",
        conversation_id=conversation_id,
        user_id="user-456",
        text="Need flight Mum-Del Nov 11",
        sender_is_traveler=True,
        group_id=conversation_id,
    )
    app.orchestrator(
        channel="whatsapp_group",
        conversation_id=conversation_id,
        user_id="user-456",
        text="F1",
        sender_is_traveler=True,
        group_id=conversation_id,
    )
    response = app.orchestrator(
        channel="whatsapp_group",
        conversation_id=conversation_id,
        user_id="user-456",
        text="CONFIRM F1",
        sender_is_traveler=False,
        group_id=conversation_id,
    )
    assert "Only the mapped traveler" in response


def test_hold_expiry_requires_reconfirm():
    reset_storage()
    conversation_id = "group-789"
    app.whatsapp_adapter.register_group(conversation_id, "user-789", "+918888888888")

    app.orchestrator(
        channel="whatsapp_group",
        conversation_id=conversation_id,
        user_id="user-789",
        text="Need Mum-Del Nov 11 flights",
        sender_is_traveler=True,
        group_id=conversation_id,
    )
    app.orchestrator(
        channel="whatsapp_group",
        conversation_id=conversation_id,
        user_id="user-789",
        text="F2",
        sender_is_traveler=True,
        group_id=conversation_id,
    )
    stored = app.storage.load(conversation_id)
    stored["itinerary"]["hold_until"] = (timeutil.now_ist() - timedelta(minutes=10)).isoformat()
    app.storage.save(conversation_id, stored)
    response = app.orchestrator(
        channel="whatsapp_group",
        conversation_id=conversation_id,
        user_id="user-789",
        text="CONFIRM F2",
        sender_is_traveler=True,
        group_id=conversation_id,
    )
    assert "Hold expired" in response
