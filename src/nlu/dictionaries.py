from __future__ import annotations

CITY_SYNONYMS = {
    "mumbai": "BOM",
    "mum": "BOM",
    "bom": "BOM",
    "bombay": "BOM",
    "delhi": "DEL",
    "del": "DEL",
    "new delhi": "DEL",
    "delhi ncr": "DEL",
}

AIRLINE_SYNONYMS = {
    "vistara": "UK",
    "air india": "AI",
    "indigo": "6E",
    "spicejet": "SG",
}

LANDMARKS = {
    "aerocity": {"type": "landmark", "name": "Aerocity", "radiusKm": 4},
}

SEAT_MAP = {
    "aisle": "AISLE",
    "window": "WINDOW",
    "any": "ANY",
}

MEAL_MAP = {
    "veg": "VEG",
    "vegetarian": "VEG",
    "non veg": "NON_VEG",
    "non-veg": "NON_VEG",
    "any": "ANY",
}

CABIN_MAP = {
    "economy": "ECONOMY",
    "premium economy": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
    "first": "FIRST",
}
