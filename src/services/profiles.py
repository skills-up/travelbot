from __future__ import annotations

from typing import Dict

from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    traveler_id: str
    contact_id: str
    name: str
    class_pref: str = "ECONOMY"
    seat_pref: str = "AISLE"
    meal_pref: str = "VEG"
    airlines: list[str] = []


class ProfileService:
    def __init__(self):
        self._profiles: Dict[str, UserProfile] = {}

    def get(self, user_id: str) -> UserProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(
                user_id=user_id,
                traveler_id=f"trav_{user_id}",
                contact_id=f"contact_{user_id}",
                name=f"Traveler {user_id}",
            )
        return self._profiles[user_id]
