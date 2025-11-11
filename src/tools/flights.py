from __future__ import annotations

from datetime import date, time, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from ..services.timeutil import add_minutes, now_ist


class TimeWindow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: time = Field(alias="from")
    to: time


class Pax(BaseModel):
    adults: int = 1
    children: int = 0
    infants: int = 0


class Prefs(BaseModel):
    seat: str = "ANY"
    meal: str = "ANY"
    airlines: List[str] = Field(default_factory=list)


class Filters(BaseModel):
    nonstop: bool | None = None


class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departDate: date
    timeWindow: Optional[TimeWindow] = None
    pax: Pax = Field(default_factory=Pax)
    cabin: str = "ECONOMY"
    prefs: Prefs = Field(default_factory=Prefs)
    filters: Filters = Field(default_factory=Filters)


class FlightOption(BaseModel):
    offerId: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    depart: str
    arrive: str
    depart_date: date
    arrival_date: date
    cabin: str
    nonstop: bool
    stops: str
    baggage: str
    fare_brand: str
    currency: str
    amount: int


class FlightSearchResponse(BaseModel):
    offers: List[FlightOption]


class FlightRepriceRequest(BaseModel):
    offerId: str
    hold: bool = True


class FlightRepriceResponse(BaseModel):
    offerId: str
    amount: int
    currency: str
    holdUntil: datetime


class FlightBookRequest(BaseModel):
    offerId: str
    travelerId: str
    contactId: str
    ancillaries: dict
    idempotencyKey: str


class FlightBookResponse(BaseModel):
    pnr: str
    ticket_numbers: List[str]


class FlightIssueRequest(BaseModel):
    pnr: str
    idempotencyKey: str


class FlightIssueResponse(BaseModel):
    pnr: str
    ticket_numbers: List[str]


class FlightsClient:
    def search(self, request: FlightSearchRequest) -> FlightSearchResponse:
        offers = [
            FlightOption(
                offerId="OFF1",
                airline="AI",
                flight_number="678",
                origin=request.origin,
                destination=request.destination,
                depart="16:05",
                arrive="18:15",
                depart_date=request.departDate,
                arrival_date=request.departDate,
                cabin=request.cabin,
                nonstop=True,
                stops="Nonstop",
                baggage="25kg",
                fare_brand="ECONOMY",
                currency="INR",
                amount=7900,
            ),
            FlightOption(
                offerId="OFF2",
                airline="UK",
                flight_number="933",
                origin=request.origin,
                destination=request.destination,
                depart="15:20",
                arrive="17:30",
                depart_date=request.departDate,
                arrival_date=request.departDate,
                cabin=request.cabin,
                nonstop=True,
                stops="Nonstop",
                baggage="15kg",
                fare_brand="ECONOMY",
                currency="INR",
                amount=8200,
            ),
            FlightOption(
                offerId="OFF3",
                airline="6E",
                flight_number="5313",
                origin=request.origin,
                destination=request.destination,
                depart="15:45",
                arrive="18:50",
                depart_date=request.departDate,
                arrival_date=request.departDate,
                cabin="PREMIUM_ECONOMY",
                nonstop=False,
                stops="1 stop",
                baggage="15kg",
                fare_brand="SMART",
                currency="INR",
                amount=6950,
            ),
        ]
        return FlightSearchResponse(offers=offers[:3])

    def reprice(self, request: FlightRepriceRequest) -> FlightRepriceResponse:
        hold_until = add_minutes(now_ist(), 45)
        return FlightRepriceResponse(
            offerId=request.offerId,
            amount=8200 if request.offerId == "OFF2" else 7900,
            currency="INR",
            holdUntil=hold_until,
        )

    def book(self, request: FlightBookRequest) -> FlightBookResponse:
        return FlightBookResponse(pnr="PNR123", ticket_numbers=["0987654321", "0987654322"])

    def issue(self, request: FlightIssueRequest) -> FlightIssueResponse:
        return FlightIssueResponse(pnr=request.pnr, ticket_numbers=["0987654321", "0987654322"])
