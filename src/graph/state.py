from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from ..nlu.parser import ParsedIntent
from ..services.profiles import UserProfile


class FlightOptionState(BaseModel):
    offer_id: str
    code: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    depart: str
    arrive: str
    depart_date: str
    arrival_date: str
    cabin: str
    baggage: str
    currency: str
    amount: int
    fare_brand: str
    nonstop: bool
    stops: str


class HotelOptionState(BaseModel):
    rate_id: str
    code: str
    name: str
    rating: float
    board: str
    currency: str
    amount: int
    check_in: str
    check_out: str


class Itinerary(BaseModel):
    flight_options: List[FlightOptionState] = Field(default_factory=list)
    hotel_options: List[HotelOptionState] = Field(default_factory=list)
    selected_flight_id: Optional[str] = None
    selected_hotel_id: Optional[str] = None
    hold_until: Optional[datetime] = None
    confirm_ready: bool = False
    booked: bool = False
    pnr: Optional[str] = None
    ticket_numbers: List[str] = Field(default_factory=list)
    hotel_conf: Optional[str] = None


class ConversationState(BaseModel):
    channel: str
    group_id: Optional[str] = None
    user_id: str
    profile: UserProfile
    entities: Optional[ParsedIntent] = None
    itinerary: Itinerary = Field(default_factory=Itinerary)
    last_message_text: Optional[str] = None
    last_outbound_text: Optional[str] = None
    sender_is_traveler: bool = True
    dm_required: bool = False
    last_error: Optional[str] = None


def make_conversation_state(channel: str, user_id: str, profile: UserProfile, group_id: Optional[str] = None) -> ConversationState:
    return ConversationState(channel=channel, user_id=user_id, profile=profile, group_id=group_id)
