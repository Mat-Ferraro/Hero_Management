from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Item:
    name: str
    slot: str
    stat_bonuses: Dict[str, int]
    value: int
    rarity: str = "Common"
    damage_type_bonus: Dict[str, float] = field(default_factory=dict)
    enemy_type_bonus: Dict[str, float] = field(default_factory=dict)
    enemy_type_resistance: Dict[str, float] = field(default_factory=dict)
    class_restrictions: List[str] = field(default_factory=list)
    enemy_affinity: List[str] = field(default_factory=list)

    def can_equip(self, hero_class: str) -> bool:
        return not self.class_restrictions or hero_class in self.class_restrictions

    def display(self) -> str:
        parts = []

        if self.stat_bonuses:
            parts.append(", ".join(f"+{value} {stat}" for stat, value in self.stat_bonuses.items()))

        if self.damage_type_bonus:
            parts.append(", ".join(f"+{int(value * 100)}% {damage} damage" for damage, value in self.damage_type_bonus.items()))

        if self.enemy_type_bonus:
            parts.append(", ".join(f"+{int(value * 100)}% vs {enemy}" for enemy, value in self.enemy_type_bonus.items()))

        if self.enemy_type_resistance:
            parts.append(", ".join(f"-{int(value * 100)}% dmg from {enemy}" for enemy, value in self.enemy_type_resistance.items()))

        restrictions = ""
        if self.class_restrictions:
            restrictions = f" | Classes: {', '.join(self.class_restrictions)}"

        detail = "; ".join(parts) if parts else "No bonuses"
        return f"{self.name} [{self.rarity} {self.slot}] ({detail}) - value {self.value}g{restrictions}"
