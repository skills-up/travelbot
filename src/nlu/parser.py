from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time
from typing import List, Optional

from pydantic import BaseModel, Field

from .dictionaries import (
    AIRLINE_SYNONYMS,
    CABIN_MAP,
    CITY_SYNONYMS,
    LANDMARKS,
    MEAL_MAP,
    SEAT_MAP,
)
from ..services import timeutil


class ParsedIntent(BaseModel):
    want_flights: bool = False
    want_hotels: bool = False
    origin: Optional[str] = None
    destination: Optional[str] = None
    depart_date: Optional[date] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    rooms: Optional[int] = None
    pax_adults: Optional[int] = None
    class_pref: Optional[str] = None
    seat_pref: Optional[str] = None
    meal_pref: Optional[str] = None
    airlines: List[str] = Field(default_factory=list)
    landmark: Optional[str] = None
    selection_flights: List[str] = Field(default_factory=list)
    selection_hotels: List[str] = Field(default_factory=list)
    confirm_codes: List[str] = Field(default_factory=list)
    is_confirm: bool = False


class LLMClient:
    """Optional abstraction for a structured-output LLM."""

    def parse_intent(self, text: str) -> Optional[ParsedIntent]:  # pragma: no cover - interface only
        raise NotImplementedError


@dataclass
class Parser:
    llm_client: Optional[LLMClient] = None

    def parse(self, text: str) -> ParsedIntent:
        heuristics = self._heuristic_parse(text)
        if self.llm_client:
            try:
                llm_result = self.llm_client.parse_intent(text)
            except Exception:
                llm_result = None
            if llm_result:
                return self._merge(heuristics, llm_result)
        return heuristics

    def _merge(self, base: ParsedIntent, other: ParsedIntent) -> ParsedIntent:
        data = base.model_dump()
        for key, value in other.model_dump().items():
            if value in (None, [], False):
                continue
            data[key] = value
        return ParsedIntent(**data)

    def _heuristic_parse(self, text: str) -> ParsedIntent:
        lowered = text.lower()
        want_flights = any(token in lowered for token in ["flight", "flt", "fly", "f1", "f2", "f3"])
        want_hotels = any(token in lowered for token in ["hotel", "stay", "room", "h1", "h2", "h3"])
        origin, destination = self._extract_city_pair(lowered)
        depart_date = self._extract_depart_date(lowered)
        time_from, time_to = timeutil.parse_time_window(lowered)
        check_in, check_out = self._extract_hotel_dates(lowered)
        rooms = self._extract_rooms(lowered)
        pax = self._extract_pax(lowered)
        class_pref = self._match_map(lowered, CABIN_MAP)
        seat_pref = self._match_map(lowered, SEAT_MAP)
        meal_pref = self._match_map(lowered, MEAL_MAP)
        airlines = self._extract_airlines(lowered)
        landmark = self._extract_landmark(lowered)
        selection_flights, selection_hotels, is_confirm, confirm_codes = self._extract_commands(text)
        return ParsedIntent(
            want_flights=want_flights or bool(origin and destination),
            want_hotels=want_hotels or bool(landmark or check_in),
            origin=origin,
            destination=destination,
            depart_date=depart_date,
            time_from=time_from,
            time_to=time_to,
            check_in=check_in,
            check_out=check_out,
            rooms=rooms,
            pax_adults=pax,
            class_pref=class_pref,
            seat_pref=seat_pref,
            meal_pref=meal_pref,
            airlines=airlines,
            landmark=landmark,
            selection_flights=selection_flights,
            selection_hotels=selection_hotels,
            is_confirm=is_confirm,
            confirm_codes=confirm_codes,
        )

    def _extract_city_pair(self, lowered: str) -> tuple[Optional[str], Optional[str]]:
        pair_match = re.search(r"([a-z]{3,})\s*(?:-|→|\sto\s)\s*([a-z]{3,})", lowered)
        if pair_match:
            origin_raw, dest_raw = pair_match.groups()
            return self._city_to_iata(origin_raw), self._city_to_iata(dest_raw)
        tokens = lowered.split()
        if "from" in tokens and "to" in tokens:
            try:
                origin_raw = tokens[tokens.index("from") + 1]
                dest_raw = tokens[tokens.index("to") + 1]
                return self._city_to_iata(origin_raw), self._city_to_iata(dest_raw)
            except (ValueError, IndexError):
                pass
        return None, None

    def _city_to_iata(self, token: str) -> Optional[str]:
        token = token.strip().lower()
        return CITY_SYNONYMS.get(token)

    def _extract_depart_date(self, lowered: str):
        match = re.search(r"(nov\.?\s*\d{1,2}(?:st|nd|rd|th)?)", lowered)
        if match:
            return timeutil.parse_date(match.group(1))
        return timeutil.parse_date(lowered)

    def _extract_hotel_dates(self, lowered: str):
        range_match = re.search(r"(nov\.?\s*\d{1,2}(?:st|nd|rd|th)?\s*(?:-|to)\s*\d{1,2})", lowered)
        if range_match:
            start, end = timeutil.parse_date_range(range_match.group(1))
            return start, end
        check_in = None
        check_out = None
        check_in_match = re.search(r"check in\s*(\w+\s*\d{1,2}(?:st|nd|rd|th)?)", lowered)
        if check_in_match:
            check_in = timeutil.parse_date(check_in_match.group(1))
        check_out_match = re.search(r"check out\s*(\w+\s*\d{1,2}(?:st|nd|rd|th)?)", lowered)
        if check_out_match:
            check_out = timeutil.parse_date(check_out_match.group(1))
        return check_in, check_out

    def _extract_rooms(self, lowered: str) -> Optional[int]:
        match = re.search(r"rooms?\s*(\d+)", lowered)
        if match:
            return int(match.group(1))
        return None

    def _extract_pax(self, lowered: str) -> Optional[int]:
        match = re.search(r"pax\s*(\d+)|passengers?\s*(\d+)|adults?\s*(\d+)", lowered)
        if match:
            for group in match.groups():
                if group:
                    return int(group)
        return None

    def _match_map(self, lowered: str, mapping: dict[str, str]) -> Optional[str]:
        for key, value in mapping.items():
            if key in lowered:
                return value
        return None

    def _extract_airlines(self, lowered: str) -> List[str]:
        found = []
        for key, code in AIRLINE_SYNONYMS.items():
            if key in lowered and code not in found:
                found.append(code)
        return found[:5]

    def _extract_landmark(self, lowered: str) -> Optional[str]:
        for key in LANDMARKS:
            if key in lowered:
                return key
        return None

    def _extract_commands(self, original: str):
        confirm_match = re.search(r"confirm\s+([^\n]+)", original, flags=re.I)
        confirm_codes: List[str] = []
        is_confirm = False
        if confirm_match:
            is_confirm = True
            confirm_codes = re.findall(r"(F\d+|H\d+)", confirm_match.group(1), flags=re.I)
        filtered_text = original
        if confirm_match:
            filtered_text = original.replace(confirm_match.group(0), "")
        selection_flights = re.findall(r"\b(F\d+)\b", filtered_text, flags=re.I)
        selection_hotels = re.findall(r"\b(H\d+)\b", filtered_text, flags=re.I)
        return [code.upper() for code in selection_flights], [code.upper() for code in selection_hotels], is_confirm, [code.upper() for code in confirm_codes]
