"""Allowed values for enumerated columns. Stored as plain strings."""

from enum import Enum


class Sex(str, Enum):
    male = "male"
    female = "female"


class Goal(str, Enum):
    lose_fat = "lose_fat"
    build_muscle = "build_muscle"
    stay_fit = "stay_fit"


class Level(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class DietType(str, Enum):
    veg = "veg"
    egg = "egg"
    non_veg = "non_veg"
