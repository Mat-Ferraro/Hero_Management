from dataclasses import dataclass
from typing import List


@dataclass
class RoomOption:
    room_type: str
    description: str


@dataclass
class RoomResolution:
    messages: List[str]
    loot: int
    xp: int
    party_wiped: bool = False
