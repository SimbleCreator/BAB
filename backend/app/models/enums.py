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


class Source(str, Enum):
    """Where an activity record came from. Automatic sources replace manual ones later."""

    manual = "manual"
    csv = "csv"
    gpx = "gpx"
    android = "android"
    ios = "ios"


class TrainingMode(str, Enum):
    """Activity: walking, jogging and home bodyweight work. Gym: gym training. Both."""

    activity = "activity"
    gym = "gym"
    both = "both"


class WorkType(str, Enum):
    """How the user spends most of the working day."""

    desk = "desk"
    standing = "standing"  # on your feet
    physical = "physical"
    shifts = "shifts"


class FoodSource(str, Enum):
    """Where most of the user's food comes from."""

    home = "home"
    hostel = "hostel"  # hostel or mess
    out = "out"  # eating out
    mixed = "mixed"
