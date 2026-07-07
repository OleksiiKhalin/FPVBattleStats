from enum import Enum


class RaceClass(str, Enum):
    OPEN = "open"
    WHOOP = "whoop"


class Category(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    UNRANKED = "unranked"

