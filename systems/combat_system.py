import random
from typing import List

from combat_types import effective_power_against_enemy, incoming_damage_multiplier
from game_state import GameState
from hero_specialties import (
    apply_life_cleric_healing,
    has_specialty,
    first_room_damage_multiplier,
    specialty_combat_power_bonus,
    try_grave_cleric_save,
    wound_chance_multiplier,
    xp_multiplier,
)
from manager_reputation import (
    reputation_for_death,
    reputation_for_room_outcome,
    reputation_for_wound,
)
from models import Dungeon, Hero
from .death_system import queue_bereavement_payment, recover_equipment_from_dead_hero
from .room_resolution import RoomResolution
from ui import danger, highlight, info, success, warning


def effective_party_power_for_room_against_enemy(party: List[Hero], room_type: str, enemy_type: str) -> int:
    total = 0

    for hero in party:
        base_power = hero.combat_power()
        base_power += specialty_combat_power_bonus(hero, room_type)
        total += effective_power_against_enemy(hero, enemy_type, base_power)

    return max(1, total)

def estimate_success_chance(
    party: List[Hero],
    enemy_power: int,
    room_type: str = "Monster",
    enemy_type: str = "Beasts",
) -> float:
    party_power = effective_party_power_for_room_against_enemy(party, room_type, enemy_type)
    if party_power <= 0:
        return 0.0
    return party_power / (party_power + enemy_power)

def apply_room_damage_and_casualties(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    enemy_power: int,
    combat_outcome: str,
    room_number: int,
) -> List[str]:
    messages = []

    if combat_outcome == "dominant":
        risk_multiplier = 0.45
    elif combat_outcome == "stable":
        risk_multiplier = 0.80
    elif combat_outcome == "rough":
        risk_multiplier = 1.20
    else:
        risk_multiplier = 1.60

    risk_multiplier *= first_room_damage_multiplier(party, room_number)

    party_power = max(1, effective_party_power_for_room_against_enemy(party, "Monster", dungeon.enemy_type))
    danger_ratio = enemy_power / party_power

    pending_dead_heroes: List[Hero] = []

    for hero in list(party):
        base_damage = random.randint(8, 18)
        scaled_damage = int(base_damage * danger_ratio * risk_multiplier * dungeon.difficulty)
        damage = max(2, int(scaled_damage * incoming_damage_multiplier(hero, dungeon.enemy_type)))

        damage_message = hero.take_damage(damage)

        if hero.health_status() in ("DEAD", "CRITICAL"):
            messages.append(danger(damage_message))
        elif hero.health_status() in ("WOUNDED", "HURT"):
            messages.append(warning(damage_message))
        else:
            messages.append(success(damage_message))

        if hero.current_health is not None and hero.current_health <= 0:
            grave_messages = try_grave_cleric_save(party, hero)
            messages.extend(grave_messages)

            if hero.current_health is not None and hero.current_health > 0:
                continue

            guardians = [
                ally for ally in party
                if ally is not hero
                and getattr(ally, "specialty", "") == "Guardian"
                and getattr(ally, "current_health", 0) > 0
            ]

            if guardians:
                guardian = guardians[0]
                guardian_damage = max(1, int(guardian.max_health() * 0.35))
                messages.append(highlight(f"{guardian.name} uses Guardian to prevent {hero.name}'s death."))
                hero.current_health = max(1, int(hero.max_health() * 0.10))
                messages.append(success(f"{hero.name} survives at {hero.current_health}/{hero.max_health()} HP."))
                messages.append(warning(guardian.take_damage(guardian_damage)))

                if guardian.current_health and guardian.current_health > 0:
                    continue

            party.remove(hero)
            pending_dead_heroes.append(hero)

            if hero in state.roster:
                state.roster.remove(hero)

            if not hero.is_temporary_survivor:
                state.fallen_heroes.append(hero)

            if hero.is_temporary_survivor:
                messages.append(danger(f"!!! {hero.name.upper()} THE TEMPORARY SURVIVOR WAS KILLED !!!"))
            else:
                messages.append(danger(f"!!! {hero.name.upper()} WAS KILLED !!!"))
                messages.append(queue_bereavement_payment(state, hero))

            messages.extend(reputation_for_death(state.reputation, hero.hero_class, hero.is_temporary_survivor))
            continue

        health_risk = 1.0
        if hero.health_percent() < 0.25:
            health_risk = 3.0
        elif hero.health_percent() < 0.50:
            health_risk = 1.8

        wound_multiplier = wound_chance_multiplier(party)
        mortal_roll = dungeon.mortal_wound_chance * risk_multiplier * health_risk * wound_multiplier
        minor_roll = dungeon.minor_wound_chance * risk_multiplier * health_risk * wound_multiplier

        roll = random.random()
        if roll < mortal_roll:
            messages.append(danger(hero.apply_mortal_wound()))
            messages.extend(reputation_for_wound(state.reputation, hero.hero_class, "mortal"))
        elif roll < mortal_roll + minor_roll:
            messages.append(warning(hero.apply_minor_wound()))
            messages.extend(reputation_for_wound(state.reputation, hero.hero_class, "minor"))

    party_has_survivors = len(party) > 0
    for dead_hero in pending_dead_heroes:
        messages.extend(recover_equipment_from_dead_hero(state, dead_hero, party_has_survivors))

    return messages

def resolve_combat_room(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    room_number: int,
    room_type: str,
) -> RoomResolution:
    messages = []
    enemy_type = dungeon.enemy_type_for_room(room_type)
    messages.append(info(f"Enemy type: {enemy_type}."))
    enemy_power = dungeon.room_enemy_power(room_number, room_type)
    success_chance = estimate_success_chance(party, enemy_power, room_type, enemy_type)
    roll = random.random()

    specialty_bonus_lines = []
    for hero in party:
        bonus = specialty_combat_power_bonus(hero, room_type)
        if bonus > 0:
            specialty_bonus_lines.append(f"{hero.name}'s {hero.specialty} adds +{bonus} effective power.")

    for line in specialty_bonus_lines:
        messages.append(highlight(line))

    if roll <= success_chance * 0.55:
        combat_outcome = "dominant"
        messages.append(success(f"{room_type} encounter went extremely well. The party dominated the fight."))
        loot_multiplier = 1.15
        xp_base_multiplier = 1.15
    elif roll <= success_chance:
        combat_outcome = "stable"
        messages.append(success(f"{room_type} encounter was cleared. The party held formation."))
        loot_multiplier = 1.0
        xp_base_multiplier = 1.0
    elif roll <= min(0.95, success_chance + 0.25):
        combat_outcome = "rough"
        messages.append(warning(f"{room_type} encounter was costly. The party survived, but took a beating."))
        loot_multiplier = 0.65
        xp_base_multiplier = 0.85
    else:
        combat_outcome = "disaster"
        messages.append(danger(f"{room_type} encounter became a disaster. The party barely escaped the enemy."))
        loot_multiplier = 0.35
        xp_base_multiplier = 0.50

    messages.extend(reputation_for_room_outcome(state.reputation, room_type, combat_outcome))

    room_loot = int((random.randint(dungeon.loot_min, dungeon.loot_max) / dungeon.room_count) * loot_multiplier)
    room_xp = int((dungeon.xp_reward / dungeon.room_count) * xp_base_multiplier * xp_multiplier(party))

    if has_specialty(party, "Scholar"):
        messages.append(highlight("Scholar specialty increases combat XP earned."))

    if room_type == "Elite":
        room_loot = int(room_loot * 1.45)
        room_xp = int(room_xp * 1.35)
    elif room_type == "Boss":
        room_loot = int(room_loot * 2.0)
        room_xp = int(room_xp * 1.75)

    messages.append(success(f"Potential room loot: {room_loot}g."))
    messages.append(info(f"Combat XP earned: {room_xp}."))

    messages.extend(
        apply_room_damage_and_casualties(
            state=state,
            party=party,
            dungeon=dungeon,
            enemy_power=enemy_power,
            combat_outcome=combat_outcome,
            room_number=room_number,
        )
    )

    if not party:
        messages.append(danger(f"The party was wiped out. The {room_loot}g from this room is lost in the dungeon."))
        return RoomResolution(messages=messages, loot=0, xp=0, party_wiped=True)

    messages.extend(apply_life_cleric_healing(party))
    return RoomResolution(messages=messages, loot=room_loot, xp=room_xp, party_wiped=False)

