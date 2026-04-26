import random
from typing import List

from game_state import GameState, create_item_pool, refresh_contract_market
from models import Dungeon, Hero, Item


def estimate_success_chance(party: List[Hero], enemy_power: int) -> float:
    party_power = sum(hero.combat_power() for hero in party)
    if party_power <= 0:
        return 0.0
    return party_power / (party_power + enemy_power)


def pay_expedition_wages(state: GameState) -> List[str]:
    messages = ["=== Expedition Wages ==="]

    for hero in list(state.roster):
        if state.gold >= hero.wage_per_expedition:
            state.gold -= hero.wage_per_expedition
            messages.append(f"Paid {hero.name} {hero.wage_per_expedition}g.")
        else:
            state.roster.remove(hero)
            messages.append(f"Could not pay {hero.name}'s {hero.wage_per_expedition}g wage. {hero.name} leaves the guild.")

    return messages


def apply_stage_damage_and_casualties(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    stage_success: bool,
    enemy_power: int,
) -> List[str]:
    messages = []
    risk_multiplier = 0.75 if stage_success else 1.45
    party_power = max(1, sum(hero.combat_power() for hero in party))
    danger_ratio = enemy_power / party_power

    for hero in list(party):
        base_damage = random.randint(8, 18)
        scaled_damage = int(base_damage * danger_ratio * risk_multiplier * dungeon.difficulty)
        damage = max(3, scaled_damage)
        messages.append(hero.take_damage(damage))

        if hero.current_health is not None and hero.current_health <= 0:
            party.remove(hero)
            if hero in state.roster:
                state.roster.remove(hero)
            state.fallen_heroes.append(hero)
            messages.append(f"{hero.name} died from their wounds.")
            continue

        health_risk = 1.0
        if hero.health_percent() < 0.25:
            health_risk = 3.0
        elif hero.health_percent() < 0.50:
            health_risk = 1.8

        mortal_roll = dungeon.mortal_wound_chance * risk_multiplier * health_risk
        minor_roll = dungeon.minor_wound_chance * risk_multiplier * health_risk

        roll = random.random()
        if roll < mortal_roll:
            messages.append(hero.apply_mortal_wound())
        elif roll < mortal_roll + minor_roll:
            messages.append(hero.apply_minor_wound())

    return messages


def generate_item_drop(dungeon: Dungeon) -> Item:
    item = random.choice(create_item_pool())

    if dungeon.difficulty >= 4 and random.random() < 0.35:
        return Item(
            f"Masterwork {item.name}",
            item.slot,
            {stat: value + 2 for stat, value in item.stat_bonuses.items()},
            int(item.value * 2.2),
        )

    if dungeon.difficulty >= 3 and random.random() < 0.5:
        return Item(
            f"Fine {item.name}",
            item.slot,
            {stat: value + 1 for stat, value in item.stat_bonuses.items()},
            int(item.value * 1.5),
        )

    return item


def simulate_multi_stage_dungeon(state: GameState, party: List[Hero], dungeon: Dungeon) -> List[str]:
    for hero in party:
        hero.reset_health_for_expedition()

    messages = ["=== Dungeon Expedition Begins ===", f"Dungeon: {dungeon.name}"]
    completed_stages = 0
    loot_earned = 0
    xp_earned = 0

    for stage in range(1, dungeon.stages + 1):
        if not party:
            messages.append("No heroes remain. The expedition has failed.")
            break

        enemy_power = dungeon.stage_enemy_power(stage)
        party_power = sum(hero.combat_power() for hero in party)
        success_chance = estimate_success_chance(party, enemy_power)

        print("\n" + "-" * 60)
        print(f"Stage {stage}/{dungeon.stages}: {dungeon.name}")
        print(f"Current Party Power: {party_power}")
        print(f"Stage Enemy Power: {enemy_power}")
        print(f"Estimated Stage Success Chance: {success_chance * 100:.1f}%")
        print(f"Loot Secured So Far: {loot_earned}g")
        print("Party Status:")

        for hero in party:
            print(f"  - {hero.display_short()}")

        if stage > 1:
            choice = input("Continue deeper? [y/N]: ").strip().lower()
            if choice != "y":
                messages.append(f"The party retreats after clearing {completed_stages} stage(s).")
                break

        stage_success = random.random() <= success_chance

        if stage_success:
            completed_stages += 1
            stage_loot = random.randint(dungeon.loot_min, dungeon.loot_max) // dungeon.stages
            stage_xp = max(1, dungeon.xp_reward // dungeon.stages)
            loot_earned += stage_loot
            xp_earned += stage_xp
            messages.append(f"Stage {stage} cleared. Secured {stage_loot}g and {stage_xp} XP value.")
        else:
            partial_loot = random.randint(dungeon.loot_min // 10, dungeon.loot_max // 6) // dungeon.stages
            loot_earned += partial_loot
            messages.append(f"Stage {stage} failed. The party salvaged {partial_loot}g while escaping the immediate threat.")

        messages.extend(apply_stage_damage_and_casualties(state, party, dungeon, stage_success, enemy_power))

        if not stage_success:
            choice = input("The stage was failed. Try to push onward anyway? [y/N]: ").strip().lower()
            if choice != "y":
                messages.append("The party abandons the expedition.")
                break

    state.gold += loot_earned
    messages.append(f"Total expedition loot: {loot_earned}g.")

    if completed_stages == dungeon.stages:
        messages.append("The dungeon was fully cleared!")
        if random.random() < dungeon.item_drop_chance:
            item = generate_item_drop(dungeon)
            state.inventory.append(item)
            messages.append(f"The party found an item: {item.display()}")

    for hero in party:
        messages.extend(hero.add_xp(xp_earned))
        hero.current_health = None

    return messages


def finish_expedition(state: GameState, dungeon: Dungeon) -> List[str]:
    messages = ["=== Time, Contracts, and Retirement ==="]
    state.expedition += 1
    state.year += dungeon.years_to_complete

    expired_heroes = []
    retired_heroes = []

    for hero in list(state.roster):
        messages.extend(hero.advance_after_expedition(dungeon.years_to_complete))

        if hero.should_retire():
            retired_heroes.append(hero)
        elif hero.contract_expeditions <= 0:
            expired_heroes.append(hero)

    for hero in retired_heroes:
        if hero in state.roster:
            state.roster.remove(hero)
        state.retired_heroes.append(hero)
        messages.append(f"{hero.name} retires from adventuring at age {hero.age}.")

    for hero in expired_heroes:
        if hero in state.roster:
            state.roster.remove(hero)
            messages.append(f"{hero.name}'s contract has expired. They leave the guild.")

    refresh_contract_market(state)
    return messages
