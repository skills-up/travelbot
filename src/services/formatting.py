from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from ..services.timeutil import IST


def _currency_display(currency: str) -> str:
    return "₹" if currency == "INR" else currency


def format_flight_options(options: Iterable[dict]) -> str:
    lines = ["Flights (priced now):"]
    for idx, option in enumerate(options, start=1):
        lines.append(f"[ F{idx} ] {option['airline']} {option['flight_number']} {option['origin']} {option['depart']} → {option['destination']} {option['arrive']}")
        lines.append(
            f"{option['cabin']} • {'Nonstop' if option['nonstop'] else option['stops']} • {option['baggage']} • {_currency_display(option['currency'])}{option['amount']}"
        )
        lines.append("")
    lines.append("Reply: F1/F2/F3. Send F? for fare rules.")
    return "\n".join(line for line in lines if line is not None)


def format_hotel_options(options: Iterable[dict], landmark: Optional[str], check_in: Optional[str], check_out: Optional[str]) -> str:
    header = "Hotels"
    if landmark:
        header += f" ({landmark.title()}"
        if check_in and check_out:
            header += f", {check_in}–{check_out}"
        header += ")"
    lines = [header + ":"]
    for idx, option in enumerate(options, start=1):
        lines.append(
            f"[ H{idx} ] {option['name']} • {option['rating']}★ • {_currency_display(option['currency'])}{option['amount']} • {option['board']}"
        )
    lines.append("Reply: H1/H2/H3. Send H? for rate rules.")
    return "\n".join(lines)


def format_confirmation(flight: Optional[dict], hotel: Optional[dict], profile: dict, hold_until: Optional[datetime]) -> str:
    lines = ["Please confirm:"]
    if flight:
        lines.append(
            f"{flight['origin']}→{flight['destination']} {flight.get('depart_date', flight.get('date', ''))} • {flight['airline']} {flight['flight_number']} • {flight['depart']}–{flight['arrive']}"
        )
        lines.append(
            f"Traveler: {profile['name']} • {flight['cabin'].replace('_', ' ').title()} • {profile['seat_pref']} • {profile['meal_pref']}"
        )
        if hold_until:
            hold_local = hold_until.astimezone(IST)
            lines.append(
                f"Fare {_currency_display(flight['currency'])}{flight['amount']} (hold until {hold_local:%H:%M})"
            )
    if hotel:
        lines.append(
            f"Hotel: {hotel['name']} • {hotel['check_in']}–{hotel['check_out']} • {_currency_display(hotel['currency'])}{hotel['amount']}"
        )
    codes = []
    if flight:
        codes.append(flight['code'])
    if hotel:
        codes.append(hotel['code'])
    lines.append(f"Type: CONFIRM {' '.join(codes)}")
    return "\n".join(lines)


def format_final_message(pnr: Optional[str], tickets: list[str], hotel_conf: Optional[str]) -> str:
    lines = ["Booking complete:"]
    if pnr:
        lines.append(f"Flight PNR: {pnr}")
    if tickets:
        lines.append("Tickets: " + ", ".join(tickets))
    if hotel_conf:
        lines.append(f"Hotel confirmation: {hotel_conf}")
    return "\n".join(lines)


def format_hold_expired() -> str:
    return "Hold expired. Updating fares. Please review new options."
