from __future__ import annotations

from datetime import datetime, date, time, timedelta
import re
from typing import Optional, Tuple

from dateutil import parser as date_parser
from dateutil import tz

IST = tz.gettz("Asia/Kolkata")
MONTH_PATTERN = re.compile(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)", re.I)


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def normalize_year(target: datetime, reference: Optional[datetime] = None) -> datetime:
    reference = reference or now_ist()
    if target.year == reference.year:
        return target
    if target.year < reference.year:
        return target.replace(year=reference.year)
    return target


def parse_date(text: str, reference: Optional[datetime] = None) -> Optional[date]:
    reference = reference or now_ist()
    if not text:
        return None
    try:
        parsed = date_parser.parse(text, dayfirst=False, yearfirst=False, default=reference)
    except (ValueError, OverflowError):
        return None
    if not MONTH_PATTERN.search(text):
        parsed = parsed.replace(year=reference.year)
    parsed = parsed.astimezone(IST)
    return parsed.date()


def parse_date_range(text: str, reference: Optional[datetime] = None) -> Tuple[Optional[date], Optional[date]]:
    if not text:
        return None, None
    reference = reference or now_ist()
    range_match = re.search(r"(\w+\s*\d{1,2})(?:st|nd|rd|th)?\s*(?:-|to)\s*(\w+\s*\d{1,2})", text, flags=re.I)
    if range_match:
        start_raw, end_raw = range_match.groups()
        start = parse_date(start_raw, reference)
        end = parse_date(end_raw, reference)
        return start, end
    single = parse_date(text, reference)
    return single, None


def parse_time_window(text: str) -> Tuple[Optional[time], Optional[time]]:
    if not text:
        return None, None
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:-|to|–|—)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, flags=re.I)
    if not match:
        return None, None
    start_hour, start_minute, start_ampm, end_hour, end_minute, end_ampm = match.groups()

    def to_time(hour_str: str, minute_str: Optional[str], ampm: Optional[str]) -> time:
        hour = int(hour_str)
        minute = int(minute_str or 0)
        if ampm:
            ampm = ampm.lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
        return time(hour=hour, minute=minute)

    start_time = to_time(start_hour, start_minute, start_ampm)
    end_time = to_time(end_hour, end_minute, end_ampm or start_ampm)
    return start_time, end_time


def hold_expired(hold_until: Optional[datetime]) -> bool:
    if not hold_until:
        return False
    return hold_until.astimezone(IST) < now_ist()


def add_minutes(base: datetime, minutes: int) -> datetime:
    return base + timedelta(minutes=minutes)
