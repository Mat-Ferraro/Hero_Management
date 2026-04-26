from dataclasses import dataclass, field
from typing import Dict, List

from ui import danger, info, success, warning


CLASS_REPUTATION_KEYS = {
    "Warrior": "warrior",
    "Rogue": "rogue",
    "Cleric": "cleric",
    "Mage": "mage",
}


@dataclass
class ManagerReputation:
    overall: int = 0
    reliability: int = 0
    safety: int = 0
    development: int = 0
    protector: int = 0
    warrior: int = 0
    rogue: int = 0
    cleric: int = 0
    mage: int = 0
    history: List[str] = field(default_factory=list)

    def clamp_all(self) -> None:
        for key in self.scores().keys():
            value = getattr(self, key)
            setattr(self, key, max(-100, min(100, value)))

    def scores(self) -> Dict[str, int]:
        return {
            "overall": self.overall,
            "reliability": self.reliability,
            "safety": self.safety,
            "development": self.development,
            "protector": self.protector,
            "warrior": self.warrior,
            "rogue": self.rogue,
            "cleric": self.cleric,
            "mage": self.mage,
        }

    def add_history(self, text: str) -> None:
        self.history.append(text)
        if len(self.history) > 30:
            self.history = self.history[-30:]

    def adjust(self, reason: str, **changes: int) -> str:
        parts = []

        for key, amount in changes.items():
            if not hasattr(self, key):
                continue

            old_value = getattr(self, key)
            new_value = max(-100, min(100, old_value + amount))
            setattr(self, key, new_value)

            sign = "+" if amount >= 0 else ""
            parts.append(f"{key} {sign}{amount}")

        self.clamp_all()

        if not parts:
            return ""

        message = f"Reputation: {reason} ({', '.join(parts)})."
        self.add_history(message)

        if any(amount < 0 for amount in changes.values()):
            return warning(message)

        return success(message)

    def adjust_class(self, hero_class: str, amount: int, reason: str) -> str:
        key = CLASS_REPUTATION_KEYS.get(hero_class)
        if not key:
            return ""

        return self.adjust(reason, **{key: amount})

    def score_label(self, value: int) -> str:
        if value >= 50:
            return "Excellent"
        if value >= 20:
            return "Good"
        if value > -20:
            return "Neutral"
        if value > -50:
            return "Poor"
        return "Terrible"

    def display(self) -> str:
        lines = ["=== Manager Reputation ==="]

        for key, value in self.scores().items():
            label = self.score_label(value)
            lines.append(f"{key.title():<12}: {value:>4} ({label})")

        lines.append("")
        lines.append("Recent reputation events:")

        if not self.history:
            lines.append("  None yet.")
        else:
            for event in self.history[-10:]:
                lines.append(f"  - {event}")

        return "\n".join(lines)


def reputation_for_room_outcome(reputation: ManagerReputation, room_type: str, combat_outcome: str) -> List[str]:
    messages = []

    if room_type in ("Monster", "Elite", "Boss"):
        if combat_outcome == "dominant":
            messages.append(reputation.adjust(
                f"Dominated a {room_type.lower()} room",
                overall=1,
                safety=1,
            ))
        elif combat_outcome == "stable":
            messages.append(reputation.adjust(
                f"Cleared a {room_type.lower()} room cleanly",
                overall=1,
            ))
        elif combat_outcome == "rough":
            messages.append(reputation.adjust(
                f"Survived a costly {room_type.lower()} room",
                safety=-1,
            ))
        elif combat_outcome == "disaster":
            messages.append(reputation.adjust(
                f"Barely escaped a disastrous {room_type.lower()} room",
                overall=-1,
                safety=-2,
            ))

        if room_type == "Elite" and combat_outcome in ("dominant", "stable"):
            messages.append(reputation.adjust(
                "Handled an elite threat",
                overall=1,
                safety=1,
            ))

        if room_type == "Boss" and combat_outcome in ("dominant", "stable"):
            messages.append(reputation.adjust(
                "Handled a boss threat",
                overall=2,
                safety=1,
            ))

    return [message for message in messages if message]


def reputation_for_wound(reputation: ManagerReputation, hero_class: str, wound_type: str) -> List[str]:
    messages = []

    if wound_type == "minor":
        messages.append(reputation.adjust("Hero suffered a minor wound", safety=-1))
    elif wound_type == "mortal":
        messages.append(reputation.adjust("Hero suffered a mortal wound", safety=-3, overall=-1))
        messages.append(reputation.adjust_class(hero_class, -1, f"{hero_class} suffered a mortal wound"))

    return [message for message in messages if message]


def reputation_for_death(reputation: ManagerReputation, hero_class: str, is_survivor: bool) -> List[str]:
    messages = []

    if is_survivor:
        messages.append(reputation.adjust("Temporary survivor died under your command", safety=-3, protector=-4, overall=-2))
    else:
        messages.append(reputation.adjust("Contracted hero died under your command", safety=-6, overall=-4))
        messages.append(reputation.adjust_class(hero_class, -3, f"{hero_class} died under your command"))

    return [message for message in messages if message]


def reputation_for_survivor_rescued(reputation: ManagerReputation) -> List[str]:
    return [
        reputation.adjust("Safely escorted a survivor out of the dungeon", overall=2, safety=2, protector=4)
    ]


def reputation_for_debt_created(reputation: ManagerReputation) -> List[str]:
    return [
        reputation.adjust("Failed to pay wages on time", reliability=-4, overall=-1)
    ]


def reputation_for_wages_paid(reputation: ManagerReputation) -> List[str]:
    return [
        reputation.adjust("Paid yearly wages on time", reliability=1)
    ]


def reputation_for_level_up(reputation: ManagerReputation, hero_class: str) -> List[str]:
    messages = [
        reputation.adjust("Developed a hero through experience", development=2, overall=1),
        reputation.adjust_class(hero_class, 1, f"Developed a {hero_class}"),
    ]

    return [message for message in messages if message]
