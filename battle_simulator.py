import random
from typing import List

from game_state import GameState, create_item_pool, refresh_contract_market
from models import Dungeon, Hero, Item
from ui import danger, highlight, info, success, warning, bold


def estimate_success_chance(party: List[Hero], enemy_power: int) -> float:
    party_power = sum(hero.combat_power() for hero in party)
    if party_power <= 0:
        return 0.0
    return party_power / (party_power + enemy_power)


def pay_expedition_wages(state: GameState) -> List[str]:
    messages = [bold("=== Expedition Wages ===")]

    for hero in list(state.roster):
        if state.gold >= hero.wage_per_expedition:
            state.gold -= hero.wage_per_expedition
            messages.append(success(f"Paid {hero.name} {hero.wage_per_expedition}g."))
        else:
            state.roster.remove(hero)
            messages.append(
                danger(
                    f"Could not pay {hero.name}'s {hero.wage_per_expedition}g wage. "
                    f"{hero.name} leaves the guild."
                )
            )

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


def format_stage_success_chance(chance: float) -> str:
    percent = chance * 100

    if percent >= 70:
        return success(f"{percent:.1f}%")
    if percent >= 45:
        return warning(f"{percent:.1f}%")

    return danger(f"{percent:.1f}%")


def print_party_status(party: List[Hero]) -> None:
    print("Party Status:")

    for hero in party:
        line = hero.display_short()

        if hero.current_health is not None:
            if hero.health_status() in ("DEAD", "CRITICAL"):
                line = danger(line)
            elif hero.health_status() in ("WOUNDED", "HURT"):
                line = warning(line)
            else:
                line = success(line)

        print(f"  - {line}")


def print_stage_preview(
    dungeon: Dungeon,
    stage: int,
    party: List[Hero],
    enemy_power: int,
    loot_earned: int,
) -> None:
    party_power = sum(hero.combat_power() for hero in party)
    success_chance = estimate_success_chance(party, enemy_power)

    print("\n" + "-" * 60)
    print(bold(f"Stage {stage}/{dungeon.stages}: {dungeon.name}"))
    print(f"Current Party Power: {party_power}")
    print(f"Stage Enemy Power: {enemy_power}")
    print(f"Estimated Stage Success Chance: {format_stage_success_chance(success_chance)}")
    print(f"Loot Secured So Far: {success(f'{loot_earned}g')}")
    print_party_status(party)


def print_stage_result(stage_messages: List[str], party: List[Hero]) -> None:
    print("\n" + bold("STAGE RESULT"))
    print("-" * 60)

    for message in stage_messages:
        print(message)

    print("\n" + bold("Party After Stage:"))
    if not party:
        print(danger("  No heroes remain."))
    else:
        print_party_status(party)

    print("-" * 60)


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

        damage_message = hero.take_damage(damage)

        if hero.health_status() in ("DEAD", "CRITICAL"):
            messages.append(danger(damage_message))
        elif hero.health_status() in ("WOUNDED", "HURT"):
            messages.append(warning(damage_message))
        else:
            messages.append(success(damage_message))

        if hero.current_health is not None and hero.current_health <= 0:
            party.remove(hero)

            if hero in state.roster:
                state.roster.remove(hero)

            state.fallen_heroes.append(hero)
            messages.append(danger(f"!!! {hero.name.upper()} WAS KILLED !!!"))
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
            messages.append(danger(hero.apply_mortal_wound()))
        elif roll < mortal_roll + minor_roll:
            messages.append(warning(hero.apply_minor_wound()))

    return messages


def simulate_multi_stage_dungeon(state: GameState, party: List[Hero], dungeon: Dungeon) -> List[str]:
    for hero in party:
        hero.reset_health_for_expedition()

    expedition_summary = [bold("=== Dungeon Expedition Summary ==="), f"Dungeon: {dungeon.name}"]
    completed_stages = 0
    loot_earned = 0
    xp_earned = 0

    for stage in range(1, dungeon.stages + 1):
        if not party:
            expedition_summary.append(danger("No heroes remain. The expedition has failed."))
            break

        enemy_power = dungeon.stage_enemy_power(stage)
        print_stage_preview(dungeon, stage, party, enemy_power, loot_earned)

        if stage > 1:
            choice = input("Continue deeper? [y/N]: ").strip().lower()
            if choice != "y":
                expedition_summary.append(
                    warning(f"The party retreats after clearing {completed_stages} stage(s).")
                )
                break

        stage_messages = []
        success_chance = estimate_success_chance(party, enemy_power)
        stage_success = random.random() <= success_chance

        if stage_success:
            completed_stages += 1
            stage_loot = random.randint(dungeon.loot_min, dungeon.loot_max) // dungeon.stages
            stage_xp = max(1, dungeon.xp_reward // dungeon.stages)

            loot_earned += stage_loot
            xp_earned += stage_xp

            message = success(
                f"Stage {stage} cleared. Secured {stage_loot}g and {stage_xp} XP value."
            )
            stage_messages.append(message)
            expedition_summary.append(message)
        else:
            partial_loot = random.randint(dungeon.loot_min // 10, dungeon.loot_max // 6) // dungeon.stages
            loot_earned += partial_loot

            message = danger(
                f"Stage {stage} failed. The party salvaged {partial_loot}g while escaping."
            )
            stage_messages.append(message)
            expedition_summary.append(message)

        casualty_messages = apply_stage_damage_and_casualties(
            state=state,
            party=party,
            dungeon=dungeon,
            stage_success=stage_success,
            enemy_power=enemy_power,
        )

        stage_messages.extend(casualty_messages)
        expedition_summary.extend(casualty_messages)

        print_stage_result(stage_messages, party)

        if not party:
            expedition_summary.append(danger("The expedition ends because the entire party is gone."))
            break

        if not stage_success:
            choice = input("The stage failed. Try to push onward anyway? [y/N]: ").strip().lower()
            if choice != "y":
                expedition_summary.append(warning("The party abandons the expedition."))
                break

    state.gold += loot_earned
    expedition_summary.append(success(f"Total expedition loot: {loot_earned}g."))

    if completed_stages == dungeon.stages:
        expedition_summary.append(success("The dungeon was fully cleared!"))

        if random.random() < dungeon.item_drop_chance:
            item = generate_item_drop(dungeon)
            state.inventory.append(item)
            expedition_summary.append(highlight(f"The party found an item: {item.display()}"))

    for hero in party:
        xp_messages = hero.add_xp(xp_earned)

        for message in xp_messages:
            expedition_summary.append(info(message))

        hero.current_health = None

    return expedition_summary


def finish_expedition(state: GameState, dungeon: Dungeon) -> List[str]:
    messages = [bold("=== Time, Contracts, and Retirement ===")]
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
        messages.append(warning(f"{hero.name} retires from adventuring at age {hero.age}."))

    for hero in expired_heroes:
        if hero in state.roster:
            state.roster.remove(hero)
            messages.append(warning(f"{hero.name}'s contract has expired. They leave the guild."))

    refresh_contract_market(state)
    return messages