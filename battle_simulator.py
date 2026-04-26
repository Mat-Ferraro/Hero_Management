import random
from dataclasses import dataclass
from typing import List

from game_state import GameState, create_item_pool, refresh_contract_market
from models import Dungeon, Hero, Item
from ui import bold, danger, highlight, info, success, warning


COMBAT_ROOM_TYPES = {"Monster", "Elite", "Boss"}


@dataclass
class RoomOption:
    room_type: str
    description: str


def estimate_success_chance(party: List[Hero], enemy_power: int) -> float:
    party_power = sum(hero.combat_power() for hero in party)
    if party_power <= 0:
        return 0.0
    return party_power / (party_power + enemy_power)


def pay_outstanding_debts_before_expedition(state: GameState) -> List[str]:
    messages = [bold("=== Outstanding Debt Check ===")]
    any_debt = False

    for hero in list(state.roster):
        if hero.debt <= 0:
            continue

        any_debt = True
        if state.gold >= hero.debt:
            state.gold -= hero.debt
            messages.append(success(f"Paid {hero.name}'s outstanding debt of {hero.debt}g."))
            hero.debt = 0
        else:
            state.roster.remove(hero)
            messages.append(
                danger(
                    f"{hero.name} was owed {hero.debt}g. You could not clear the debt, "
                    f"so {hero.name} abandons the guild."
                )
            )

    if not any_debt:
        messages.append(success("No outstanding hero debts."))

    return messages


def pay_one_year_wages_at_expedition_start(state: GameState) -> List[str]:
    messages = [bold("=== Year 1 Wages ===")]

    for hero in list(state.roster):
        if state.gold >= hero.wage_per_year:
            state.gold -= hero.wage_per_year
            messages.append(success(f"Paid {hero.name} {hero.wage_per_year}g for the first year."))
        else:
            state.roster.remove(hero)
            messages.append(
                danger(
                    f"Could not pay {hero.name}'s first-year wage of {hero.wage_per_year}g. "
                    f"{hero.name} refuses the expedition and leaves the guild."
                )
            )

    return messages


def settle_remaining_expedition_wages_as_time_passes(state: GameState, dungeon: Dungeon) -> List[str]:
    messages = [bold("=== Expedition Wage Settlement ===")]

    if dungeon.years_to_complete <= 1:
        messages.append(success("No additional years of wages owed for this expedition."))
        return messages

    additional_years = dungeon.years_to_complete - 1
    debt_created = False

    for year_index in range(2, dungeon.years_to_complete + 1):
        messages.append(info(f"Year {year_index} wage settlement:"))

        for hero in list(state.roster):
            if state.gold >= hero.wage_per_year:
                state.gold -= hero.wage_per_year
                messages.append(success(f"  Paid {hero.name} {hero.wage_per_year}g."))
            else:
                hero.debt += hero.wage_per_year
                debt_created = True
                messages.append(
                    warning(
                        f"  Could not pay {hero.name} {hero.wage_per_year}g. "
                        f"Added to debt. Total owed: {hero.debt}g."
                    )
                )

    if debt_created:
        messages.append(
            warning(
                "Unpaid wages became debt. This should later reduce manager reliability/trust "
                "once the reputation system is added."
            )
        )
    else:
        messages.append(success(f"All wages were paid for the remaining {additional_years} year(s)."))

    return messages


def prepare_expedition_payroll(state: GameState) -> List[str]:
    messages = []
    messages.extend(pay_outstanding_debts_before_expedition(state))
    messages.extend(pay_one_year_wages_at_expedition_start(state))
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


def format_success_chance(chance: float) -> str:
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


def generate_room_options(dungeon: Dungeon, room_number: int) -> List[RoomOption]:
    if room_number >= dungeon.room_count:
        return [
            RoomOption("Boss", "Final boss encounter. High danger, strong XP and loot rewards."),
        ]

    possible_rooms = [
        RoomOption("Monster", "Enemy encounter. Grants XP and loot if defeated."),
        RoomOption("Treasure", "Loot room. No XP, but good gold/item potential. May contain traps."),
        RoomOption("Shrine", "Recovery room. Heal the party, but no XP."),
        RoomOption("Event", "Unknown event. Risk/reward outcome."),
        RoomOption("Elite", "Hard enemy encounter. Better XP and loot than a normal monster room."),
        RoomOption("Camp", "Safe rest. Small healing, no loot, no XP."),
    ]

    option_count = 3
    return random.sample(possible_rooms, option_count)


def choose_room_option(dungeon: Dungeon, room_number: int, party: List[Hero]) -> RoomOption:
    options = generate_room_options(dungeon, room_number)

    print("\n" + "-" * 60)
    print(bold(f"Room {room_number}/{dungeon.room_count}: Choose Your Path"))
    print_party_status(party)

    for index, option in enumerate(options, start=1):
        extra = ""
        if option.room_type in COMBAT_ROOM_TYPES:
            enemy_power = dungeon.room_enemy_power(room_number, option.room_type)
            chance = estimate_success_chance(party, enemy_power)
            extra = f" | Enemy Power {enemy_power} | Expected Combat Edge {format_success_chance(chance)}"

        print(f"{index}. {option.room_type}: {option.description}{extra}")

    while True:
        choice = input("Choose next room or blank to retreat: ").strip()
        if not choice:
            return RoomOption("Retreat", "The party retreats from the dungeon.")

        try:
            selected = int(choice)
        except ValueError:
            print("Please enter a valid room number.")
            continue

        if 1 <= selected <= len(options):
            return options[selected - 1]

        print(f"Please choose a number from 1 to {len(options)}.")


def print_room_result(room_messages: List[str], party: List[Hero]) -> None:
    print("\n" + bold("ROOM RESULT"))
    print("-" * 60)

    for message in room_messages:
        print(message)

    print("\n" + bold("Party After Room:"))
    if not party:
        print(danger("  No heroes remain."))
    else:
        print_party_status(party)

    print("-" * 60)


def apply_room_damage_and_casualties(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    enemy_power: int,
    combat_outcome: str,
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

    party_power = max(1, sum(hero.combat_power() for hero in party))
    danger_ratio = enemy_power / party_power

    for hero in list(party):
        base_damage = random.randint(8, 18)
        scaled_damage = int(base_damage * danger_ratio * risk_multiplier * dungeon.difficulty)
        damage = max(2, scaled_damage)

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


def resolve_combat_room(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    room_number: int,
    room_type: str,
) -> tuple[List[str], int, int]:
    messages = []
    enemy_power = dungeon.room_enemy_power(room_number, room_type)
    success_chance = estimate_success_chance(party, enemy_power)
    roll = random.random()

    if roll <= success_chance * 0.55:
        combat_outcome = "dominant"
        messages.append(success(f"{room_type} encounter went extremely well. The party dominated the fight."))
        loot_multiplier = 1.15
        xp_multiplier = 1.15
    elif roll <= success_chance:
        combat_outcome = "stable"
        messages.append(success(f"{room_type} encounter was cleared. The party held formation."))
        loot_multiplier = 1.0
        xp_multiplier = 1.0
    elif roll <= min(0.95, success_chance + 0.25):
        combat_outcome = "rough"
        messages.append(warning(f"{room_type} encounter was costly. The party survived, but took a beating."))
        loot_multiplier = 0.65
        xp_multiplier = 0.85
    else:
        combat_outcome = "disaster"
        messages.append(danger(f"{room_type} encounter became a disaster. The party barely escaped the enemy."))
        loot_multiplier = 0.35
        xp_multiplier = 0.50

    room_loot = int((random.randint(dungeon.loot_min, dungeon.loot_max) / dungeon.room_count) * loot_multiplier)
    room_xp = int((dungeon.xp_reward / dungeon.room_count) * xp_multiplier)

    if room_type == "Elite":
        room_loot = int(room_loot * 1.45)
        room_xp = int(room_xp * 1.35)
    elif room_type == "Boss":
        room_loot = int(room_loot * 2.0)
        room_xp = int(room_xp * 1.75)

    messages.append(success(f"Recovered {room_loot}g."))
    messages.append(info(f"Combat XP earned: {room_xp}."))

    messages.extend(
        apply_room_damage_and_casualties(
            state=state,
            party=party,
            dungeon=dungeon,
            enemy_power=enemy_power,
            combat_outcome=combat_outcome,
        )
    )

    return messages, room_loot, room_xp


def resolve_treasure_room(state: GameState, party: List[Hero], dungeon: Dungeon) -> tuple[List[str], int, int]:
    messages = []
    room_loot = random.randint(dungeon.loot_min, dungeon.loot_max) // max(1, dungeon.room_count - 1)
    messages.append(success(f"The party found an unguarded treasure cache worth {room_loot}g."))
    room_xp = 0

    if random.random() < 0.30:
        messages.append(warning("The treasure was trapped."))
        trap_power = int(dungeon.enemy_power * random.uniform(0.35, 0.65))
        messages.extend(
            apply_room_damage_and_casualties(
                state=state,
                party=party,
                dungeon=dungeon,
                enemy_power=trap_power,
                combat_outcome="rough",
            )
        )

    if random.random() < dungeon.item_drop_chance:
        item = generate_item_drop(dungeon)
        state.inventory.append(item)
        messages.append(highlight(f"The party found an item: {item.display()}"))

    return messages, room_loot, room_xp


def resolve_shrine_room(party: List[Hero], dungeon: Dungeon) -> tuple[List[str], int, int]:
    messages = [highlight("The party discovers a forgotten shrine.")]
    heal_amount = 12 + (dungeon.difficulty * 4)

    for hero in party:
        messages.append(success(hero.heal(heal_amount)))

    return messages, 0, 0


def resolve_camp_room(party: List[Hero], dungeon: Dungeon) -> tuple[List[str], int, int]:
    messages = [success("The party finds a defensible camp and takes time to recover.")]
    heal_amount = 8 + (dungeon.difficulty * 2)

    for hero in party:
        messages.append(success(hero.heal(heal_amount)))

    return messages, 0, 0


def resolve_event_room(state: GameState, party: List[Hero], dungeon: Dungeon) -> tuple[List[str], int, int]:
    messages = [highlight("The party encounters an unknown event.")]
    outcome = random.choice(["gold", "heal", "trap", "item", "nothing"])

    if outcome == "gold":
        room_loot = random.randint(dungeon.loot_min // 4, dungeon.loot_max // 3)
        messages.append(success(f"A strange bargain pays off. The party gains {room_loot}g."))
        return messages, room_loot, 0

    if outcome == "heal":
        heal_amount = 10 + dungeon.difficulty * 3
        messages.append(success("A mysterious force restores the party."))
        for hero in party:
            messages.append(success(hero.heal(heal_amount)))
        return messages, 0, 0

    if outcome == "trap":
        messages.append(warning("The unknown room was a trap."))
        trap_power = int(dungeon.enemy_power * random.uniform(0.45, 0.85))
        messages.extend(
            apply_room_damage_and_casualties(
                state=state,
                party=party,
                dungeon=dungeon,
                enemy_power=trap_power,
                combat_outcome="rough",
            )
        )
        return messages, 0, 0

    if outcome == "item":
        item = generate_item_drop(dungeon)
        state.inventory.append(item)
        messages.append(highlight(f"The party discovers an item: {item.display()}"))
        return messages, 0, 0

    messages.append(info("Nothing happens, which may be a blessing in this place."))
    return messages, 0, 0


def resolve_room(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    room_number: int,
    room_option: RoomOption,
) -> tuple[List[str], int, int]:
    if room_option.room_type in COMBAT_ROOM_TYPES:
        return resolve_combat_room(state, party, dungeon, room_number, room_option.room_type)

    if room_option.room_type == "Treasure":
        return resolve_treasure_room(state, party, dungeon)

    if room_option.room_type == "Shrine":
        return resolve_shrine_room(party, dungeon)

    if room_option.room_type == "Camp":
        return resolve_camp_room(party, dungeon)

    if room_option.room_type == "Event":
        return resolve_event_room(state, party, dungeon)

    return [warning("The party turns back.")], 0, 0


def simulate_multi_stage_dungeon(state: GameState, party: List[Hero], dungeon: Dungeon) -> List[str]:
    for hero in party:
        hero.reset_health_for_expedition()

    expedition_summary = [bold("=== Dungeon Expedition Summary ==="), f"Dungeon: {dungeon.name}"]
    rooms_completed = 0
    loot_earned = 0
    xp_earned = 0

    for room_number in range(1, dungeon.room_count + 1):
        if not party:
            expedition_summary.append(danger("No heroes remain. The expedition has ended."))
            break

        room_option = choose_room_option(dungeon, room_number, party)

        if room_option.room_type == "Retreat":
            expedition_summary.append(warning(f"The party retreats after completing {rooms_completed} room(s)."))
            break

        room_messages = [
            bold(f"Room {room_number}: {room_option.room_type}"),
            room_option.description,
        ]

        resolved_messages, room_loot, room_xp = resolve_room(
            state=state,
            party=party,
            dungeon=dungeon,
            room_number=room_number,
            room_option=room_option,
        )

        room_messages.extend(resolved_messages)
        loot_earned += room_loot
        xp_earned += room_xp
        rooms_completed += 1

        expedition_summary.extend(room_messages)
        print_room_result(room_messages, party)

        if not party:
            expedition_summary.append(danger("The expedition ends because the entire party is gone."))
            break

    state.gold += loot_earned
    expedition_summary.append(success(f"Total expedition loot: {loot_earned}g."))
    expedition_summary.append(info(f"Total combat XP earned: {xp_earned}."))

    if rooms_completed == dungeon.room_count and party:
        expedition_summary.append(success("The dungeon route was completed!"))

    # Only heroes who went on the quest and survived gain XP.
    # XP only comes from combat rooms.
    for hero in party:
        xp_messages = hero.add_xp(xp_earned)

        for message in xp_messages:
            expedition_summary.append(info(message))

        hero.current_health = None

    return expedition_summary


def finish_expedition(state: GameState, dungeon: Dungeon) -> List[str]:
    messages = [bold("=== Time, Contracts, Wages, and Retirement ===")]

    messages.extend(settle_remaining_expedition_wages_as_time_passes(state, dungeon))

    state.expedition += 1
    state.year += dungeon.years_to_complete

    expired_heroes = []
    retired_heroes = []

    # All roster heroes experience the passage of time, whether they went on the quest or stayed home.
    for hero in list(state.roster):
        messages.extend(hero.advance_time(dungeon.years_to_complete))

        if hero.should_retire():
            retired_heroes.append(hero)
        elif hero.contract_years <= 0:
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
