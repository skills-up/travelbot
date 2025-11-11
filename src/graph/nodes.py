from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from ..nlu.parser import Parser
from ..services import formatting, timeutil
from ..services.idempotency import IdempotencyService
from ..tools.flights import (
    FlightBookRequest,
    FlightIssueRequest,
    FlightRepriceRequest,
    FlightSearchRequest,
    FlightsClient,
    Prefs,
    Filters,
    TimeWindow,
    Pax,
)
from ..tools.hotels import HotelBookRequest, HotelSearchRequest, HotelsClient, LandmarkLocation, RoomRequest
from .state import ConversationState, FlightOptionState, HotelOptionState


@dataclass
class NodeContext:
    parser: Parser
    flights: FlightsClient
    hotels: HotelsClient
    idempotency: IdempotencyService


def make_parse_intent_node(ctx: NodeContext):
    def node(state: ConversationState) -> ConversationState:
        if not state.last_message_text:
            return state
        entities = ctx.parser.parse(state.last_message_text)
        logger.debug("Parsed intent: {}", entities)
        return state.model_copy(update={"entities": entities, "last_error": None})

    return node


def make_flight_search_node(ctx: NodeContext):
    def node(state: ConversationState) -> ConversationState:
        entities = state.entities
        if not entities or not entities.want_flights or not entities.origin or not entities.destination or not entities.depart_date:
            return state
        time_window = None
        if entities.time_from and entities.time_to:
            time_window = TimeWindow(**{"from": entities.time_from, "to": entities.time_to})
        prefs = Prefs(
            seat=entities.seat_pref or state.profile.seat_pref,
            meal=entities.meal_pref or state.profile.meal_pref,
            airlines=entities.airlines or state.profile.airlines,
        )
        request = FlightSearchRequest(
            origin=entities.origin,
            destination=entities.destination,
            departDate=entities.depart_date,
            timeWindow=time_window,
            pax=Pax(adults=entities.pax_adults or 1),
            cabin=entities.class_pref or state.profile.class_pref,
            prefs=prefs,
            filters=Filters(nonstop=True if entities.time_from else None),
        )
        response = ctx.flights.search(request)
        flight_options = []
        for idx, offer in enumerate(response.offers, start=1):
            flight_options.append(
                FlightOptionState(
                    offer_id=offer.offerId,
                    code=f"F{idx}",
                    airline=offer.airline,
                    flight_number=offer.flight_number,
                    origin=offer.origin,
                    destination=offer.destination,
                    depart=offer.depart,
                    arrive=offer.arrive,
                    depart_date=offer.depart_date.isoformat(),
                    arrival_date=offer.arrival_date.isoformat(),
                    cabin=offer.cabin,
                    baggage=offer.baggage,
                    currency=offer.currency,
                    amount=offer.amount,
                    fare_brand=offer.fare_brand,
                    nonstop=offer.nonstop,
                    stops=offer.stops,
                )
            )
        itinerary = state.itinerary.model_copy()
        itinerary.flight_options = flight_options
        itinerary.selected_flight_id = None
        itinerary.confirm_ready = False
        return state.model_copy(update={"itinerary": itinerary})

    return node


def make_hotel_search_node(ctx: NodeContext):
    def node(state: ConversationState) -> ConversationState:
        entities = state.entities
        if not entities or not entities.want_hotels or not entities.landmark or not entities.check_in or not entities.check_out:
            return state
        location = LandmarkLocation(type="landmark", name=entities.landmark.title(), radiusKm=4)
        rooms = [RoomRequest(adults=entities.pax_adults or 1) for _ in range(entities.rooms or 1)]
        request = HotelSearchRequest(
            location=location,
            checkIn=entities.check_in,
            checkOut=entities.check_out,
            rooms=rooms,
        )
        response = ctx.hotels.search(request)
        hotel_options = []
        for idx, option in enumerate(response.options, start=1):
            hotel_options.append(
                HotelOptionState(
                    rate_id=option.rateId,
                    code=f"H{idx}",
                    name=option.name,
                    rating=option.rating,
                    board=option.board,
                    currency=option.currency,
                    amount=option.amount,
                    check_in=option.check_in.isoformat(),
                    check_out=option.check_out.isoformat(),
                )
            )
        itinerary = state.itinerary.model_copy()
        itinerary.hotel_options = hotel_options
        itinerary.selected_hotel_id = None
        itinerary.confirm_ready = False
        return state.model_copy(update={"itinerary": itinerary})

    return node


def present_options_node(state: ConversationState) -> ConversationState:
    itinerary = state.itinerary
    outputs = []
    if itinerary.flight_options:
        outputs.append(
            formatting.format_flight_options(
                [
                    {
                        "airline": option.airline,
                        "flight_number": option.flight_number,
                        "origin": option.origin,
                        "destination": option.destination,
                        "depart": option.depart,
                        "arrive": option.arrive,
                        "cabin": option.cabin.title().replace("_", " "),
                        "nonstop": option.nonstop,
                        "stops": option.stops,
                        "baggage": option.baggage,
                        "currency": option.currency,
                        "amount": option.amount,
                    }
                    for option in itinerary.flight_options
                ]
            )
        )
    if itinerary.hotel_options:
        outputs.append(
            formatting.format_hotel_options(
                [
                    {
                        "name": option.name,
                        "rating": option.rating,
                        "board": option.board,
                        "currency": option.currency,
                        "amount": option.amount,
                    }
                    for option in itinerary.hotel_options
                ],
                state.entities.landmark if state.entities else None,
                itinerary.hotel_options[0].check_in if itinerary.hotel_options else None,
                itinerary.hotel_options[0].check_out if itinerary.hotel_options else None,
            )
        )
    text = "\n\n".join(outputs) if outputs else "Let me know how I can help with your travel."
    itinerary.confirm_ready = False
    return state.model_copy(update={"itinerary": itinerary, "last_outbound_text": text})


def make_select_offers_node():
    def node(state: ConversationState) -> ConversationState:
        entities = state.entities
        itinerary = state.itinerary.model_copy()
        if not entities:
            return state
        if entities.selection_flights:
            code = entities.selection_flights[-1]
            match = next((opt for opt in itinerary.flight_options if opt.code == code), None)
            if match:
                itinerary.selected_flight_id = match.offer_id
        if entities.selection_hotels:
            code = entities.selection_hotels[-1]
            match = next((opt for opt in itinerary.hotel_options if opt.code == code), None)
            if match:
                itinerary.selected_hotel_id = match.rate_id
        itinerary.confirm_ready = False
        return state.model_copy(update={"itinerary": itinerary})

    return node


def make_reprice_hold_node(ctx: NodeContext):
    def node(state: ConversationState) -> ConversationState:
        itinerary = state.itinerary.model_copy()
        entities = state.entities
        if not entities:
            return state
        hold_until = None
        if itinerary.selected_flight_id:
            response = ctx.flights.reprice(FlightRepriceRequest(offerId=itinerary.selected_flight_id))
            itinerary.hold_until = response.holdUntil
            hold_until = response.holdUntil
            match = next((opt for opt in itinerary.flight_options if opt.offer_id == response.offerId), None)
            if match:
                match.amount = response.amount
                match.currency = response.currency
        if itinerary.selected_hotel_id:
            hold_until = hold_until or timeutil.add_minutes(timeutil.now_ist(), 45)
        if itinerary.selected_flight_id or itinerary.selected_hotel_id:
            itinerary.confirm_ready = True
            profile = state.profile.model_dump()
            flight_match = None
            hotel_match = None
            if itinerary.selected_flight_id:
                flight_match = next((opt for opt in itinerary.flight_options if opt.offer_id == itinerary.selected_flight_id), None)
            if itinerary.selected_hotel_id:
                hotel_match = next((opt for opt in itinerary.hotel_options if opt.rate_id == itinerary.selected_hotel_id), None)
            text = formatting.format_confirmation(
                flight_match.model_dump() if flight_match else None,
                hotel_match.model_dump() if hotel_match else None,
                profile,
                hold_until,
            )
            return state.model_copy(update={"itinerary": itinerary, "last_outbound_text": text})
        return state.model_copy(update={"itinerary": itinerary})

    return node


def traveler_confirm_node(state: ConversationState) -> ConversationState:
    entities = state.entities
    itinerary = state.itinerary.model_copy()
    if not entities or not entities.is_confirm:
        return state
    if not state.sender_is_traveler:
        text = "Only the mapped traveler can confirm this trip."
        return state.model_copy(update={"last_outbound_text": text, "last_error": text})
    if not itinerary.confirm_ready:
        text = "We are not ready to confirm yet. Please select options first."
        return state.model_copy(update={"last_outbound_text": text, "last_error": text})
    if timeutil.hold_expired(itinerary.hold_until):
        itinerary.confirm_ready = False
        text = formatting.format_hold_expired()
        return state.model_copy(update={"itinerary": itinerary, "last_outbound_text": text, "last_error": text})
    return state.model_copy(update={"last_error": None})


def make_book_flight_node(ctx: NodeContext):
    def node(state: ConversationState) -> ConversationState:
        itinerary = state.itinerary.model_copy()
        if not itinerary.selected_flight_id or not state.entities or not state.entities.is_confirm:
            return state
        key = ctx.idempotency.new_key("flight-book")
        ctx.idempotency.store(key, itinerary.selected_flight_id)
        response = ctx.flights.book(
            FlightBookRequest(
                offerId=itinerary.selected_flight_id,
                travelerId=state.profile.traveler_id,
                contactId=state.profile.contact_id,
                ancillaries={"seats": ["12C"], "meals": [state.profile.meal_pref]},
                idempotencyKey=key,
            )
        )
        itinerary.pnr = response.pnr
        itinerary.ticket_numbers = response.ticket_numbers
        itinerary.booked = True
        return state.model_copy(update={"itinerary": itinerary})

    return node


def make_issue_ticket_node(ctx: NodeContext):
    def node(state: ConversationState) -> ConversationState:
        itinerary = state.itinerary.model_copy()
        if not itinerary.pnr:
            return state
        key = ctx.idempotency.new_key("flight-issue")
        ctx.idempotency.store(key, itinerary.pnr)
        response = ctx.flights.issue(FlightIssueRequest(pnr=itinerary.pnr, idempotencyKey=key))
        itinerary.ticket_numbers = response.ticket_numbers
        return state.model_copy(update={"itinerary": itinerary})

    return node


def make_book_hotel_node(ctx: NodeContext):
    def node(state: ConversationState) -> ConversationState:
        itinerary = state.itinerary.model_copy()
        if not itinerary.selected_hotel_id or not state.entities or not state.entities.is_confirm:
            return state
        key = ctx.idempotency.new_key("hotel-book")
        ctx.idempotency.store(key, itinerary.selected_hotel_id)
        response = ctx.hotels.book(
            HotelBookRequest(
                rateId=itinerary.selected_hotel_id,
                guestId=state.profile.traveler_id,
                contactId=state.profile.contact_id,
                idempotencyKey=key,
            )
        )
        itinerary.hotel_conf = response.confirmation
        return state.model_copy(update={"itinerary": itinerary})

    return node


def finalize_node(state: ConversationState) -> ConversationState:
    itinerary = state.itinerary
    if itinerary.pnr or itinerary.hotel_conf:
        text = formatting.format_final_message(itinerary.pnr, itinerary.ticket_numbers, itinerary.hotel_conf)
        return state.model_copy(update={"last_outbound_text": text})
    return state
