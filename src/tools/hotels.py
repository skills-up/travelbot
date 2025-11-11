from __future__ import annotations

from datetime import date
from typing import List

from pydantic import BaseModel, Field


class LandmarkLocation(BaseModel):
    type: str
    name: str
    radiusKm: int


class RoomRequest(BaseModel):
    adults: int = 1


class HotelPrefs(BaseModel):
    brands: List[str] = Field(default_factory=list)


class HotelSearchRequest(BaseModel):
    location: LandmarkLocation
    checkIn: date
    checkOut: date
    rooms: List[RoomRequest]
    prefs: HotelPrefs = Field(default_factory=HotelPrefs)


class HotelOption(BaseModel):
    rateId: str
    name: str
    rating: float
    board: str
    currency: str
    amount: int
    check_in: date
    check_out: date


class HotelSearchResponse(BaseModel):
    options: List[HotelOption]


class HotelBookRequest(BaseModel):
    rateId: str
    guestId: str
    contactId: str
    idempotencyKey: str


class HotelBookResponse(BaseModel):
    confirmation: str


class HotelsClient:
    def search(self, request: HotelSearchRequest) -> HotelSearchResponse:
        options = [
            HotelOption(
                rateId="HR1",
                name="JW Marriott",
                rating=4.8,
                board="BB",
                currency="INR",
                amount=13500,
                check_in=request.checkIn,
                check_out=request.checkOut,
            ),
            HotelOption(
                rateId="HR2",
                name="Aloft",
                rating=4.3,
                board="Room only",
                currency="INR",
                amount=8900,
                check_in=request.checkIn,
                check_out=request.checkOut,
            ),
            HotelOption(
                rateId="HR3",
                name="Andaz",
                rating=4.6,
                board="BB",
                currency="INR",
                amount=12800,
                check_in=request.checkIn,
                check_out=request.checkOut,
            ),
        ]
        return HotelSearchResponse(options=options[:3])

    def book(self, request: HotelBookRequest) -> HotelBookResponse:
        return HotelBookResponse(confirmation="HOTEL-12345")
