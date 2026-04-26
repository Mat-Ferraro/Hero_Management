import random
from dataclasses import dataclass
from typing import List

from combat_types import effective_power_against_enemy, incoming_damage_multiplier, item_matches_enemy_type, party_matchup_summary
from game_state import BereavementPayment, GameState, create_item_pool, refresh_contract_market
from hero_specialties import (
    apply_life_cleric_healing,
    describe_party_specialties,
    effective_party_power_for_room,
    first_room_damage_multiplier,
    has_specialty,
    item_drop_bonus,
    specialty_combat_power_bonus,
    treasure_gold_multiplier,
    try_grave_cleric_save,
    wound_chance_multiplier,
    xp_multiplier,
)
from manager_reputation import (
    reputation_for_death,
    reputation_for_debt_created,
    reputation_for_level_up,
    reputation_for_room_outcome,
    reputation_for_survivor_rescued,
    reputation_for_wages_paid,
    reputation_for_wound,
)
from models import Dungeon, Hero, Item
from ui import bold, danger, highlight, info, success, warning


COMBAT_ROOM_TYPES = {"Monster", "Elite", "Boss"}
EXIT_COMMANDS = {"exit", "quit", "q"}
EQUIPMENT_RECOVERY_CHANCE = 0.55


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


def is_exit_command(raw: str) -> bool:
    return raw.strip().lower() in EXIT_COMMANDS


def exit_game() -> None:
    print("Exiting game.")
    raise SystemExit


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


def prepare_expedition_payroll(state: GameState) -> List[str]:
    return pay_outstanding_debts_before_expedition(state)


def settle_pending_bereavement_payments(state: GameState) -> List[str]:
    messages = []

    if not state.pending_bereavement_payments:
        return messages

    messages.append(bold("=== Bereavement Payments ==="))

    for payment in list(state.pending_bereavement_payments):
        if state.gold >= payment.amount:
            state.gold -= payment.amount
            messages.append(success(f"Paid {payment.hero_name}'s family {payment.amount}g in bereavement wages."))
        else:
            messages.append(
                warning(
                    f"Could not afford {payment.hero_name}'s {payment.amount}g bereavement payment. "
                    f"This should hurt reliability/trust when reputation penalties are expanded."
                )
            )
            messages.extend(reputation_for_debt_created(state.reputation))

        state.pending_bereavement_payments.remove(payment)

    return messages


def settle_one_year_wages(state: GameState) -> List[str]:
    messages = [bold("=== Year-End Wage Settlement ===")]
    debt_created = False
    any_paid = False

    messages.extend(settle_pending_bereavement_payments(state))

    for hero in list(state.roster):
        if hero.is_temporary_survivor:
            continue

        if state.gold >= hero.wage_per_year:
            state.gold -= hero.wage_per_year
            any_paid = True
            messages.append(success(f"Paid {hero.name} {hero.wage_per_year}g for the year."))
        else:
            hero.debt += hero.wage_per_year
            debt_created = True
            messages.append(
                warning(
                    f"Could not pay {hero.name} {hero.wage_per_year}g. "
                    f"Added to debt. Total owed: {hero.debt}g."
                )
            )

    if any_paid and not debt_created:
        messages.extend(reputation_for_wages_paid(state.reputation))

    if debt_created:
        messages.extend(reputation_for_debt_created(state.reputation))

    return messages


def advance_one_year_after_room(state: GameState, party: List[Hero], room_number: int) -> List[str]:
    messages = [bold(f"=== End of Year {state.year} / After Room {room_number} ===")]

    messages.extend(settle_one_year_wages(state))

    state.year += 1

    expired_heroes = []
    retired_heroes = []

    for hero in list(state.roster):
        messages.extend(hero.advance_time(1))

        if hero.should_retire():
            retired_heroes.append(hero)
        elif hero.contract_years <= 0:
            expired_heroes.append(hero)

    for hero in retired_heroes:
        if hero in state.roster:
            state.roster.remove(hero)
        if hero in party:
            party.remove(hero)

        state.retired_heroes.append(hero)
        messages.append(warning(f"{hero.name} retires from adventuring at age {hero.age}."))

    for hero in expired_heroes:
        if hero in state.roster:
            state.roster.remove(hero)
        if hero in party:
            party.remove(hero)

        messages.append(warning(f"{hero.name}'s contract has expired. They leave the guild."))

    return messages


def clone_item_with_quality(item: Item, prefix: str, stat_bonus: int, value_multiplier: float, rarity: str) -> Item:
    return Item(
        name=f"{prefix} {item.name}",
        slot=item.slot,
        stat_bonuses={stat: value + stat_bonus for stat, value in item.stat_bonuses.items()},
        value=int(item.value * value_multiplier),
        rarity=rarity,
        damage_type_bonus=dict(item.damage_type_bonus),
        enemy_type_bonus=dict(item.enemy_type_bonus),
        enemy_type_resistance=dict(item.enemy_type_resistance),
        class_restrictions=list(item.class_restrictions),
        enemy_affinity=list(item.enemy_affinity),
    )


def generate_item_drop(dungeon: Dungeon, party: List[Hero] | None = None) -> Item:
    item_pool = create_item_pool()
    weighted_pool = []

    for item in item_pool:
        weight = 3

        if item_matches_enemy_type(item, dungeon.enemy_type):
            weight += 5

        if party:
            for hero in party:
                if item.can_equip(hero.hero_class):
                    weight += 1

        weighted_pool.extend([item] * max(1, weight))

    item = random.choice(weighted_pool)

    if dungeon.difficulty >= 5 and random.random() < 0.25:
        return clone_item_with_quality(item, "Legendary", 3, 3.0, "Legendary")

    if dungeon.difficulty >= 4 and random.random() < 0.35:
        return clone_item_with_quality(item, "Masterwork", 2, 2.2, "Epic")

    if dungeon.difficulty >= 3 and random.random() < 0.5:
        return clone_item_with_quality(item, "Fine", 1, 1.5, "Rare")

    return item


def create_survivor(dungeon: Dungeon) -> Hero:
    from hero_specialties import random_specialty_for_class

    survivor_class = random.choice(["Warrior", "Rogue", "Cleric", "Mage"])
    name_prefix = random.choice(["Lost", "Wounded", "Stranded", "Cornered", "Desperate"])
    name_suffix = random.choice(["Adventurer", "Mercenary", "Acolyte", "Delver", "Scout"])

    base_stat = 3 + dungeon.difficulty
    stats = {
        "might": random.randint(2, base_stat + 3),
        "agility": random.randint(2, base_stat + 3),
        "mind": random.randint(2, base_stat + 3),
        "spirit": random.randint(2, base_stat + 3),
    }

    if survivor_class == "Warrior":
        stats["might"] += 3
        stats["spirit"] += 1
    elif survivor_class == "Rogue":
        stats["agility"] += 3
        stats["might"] += 1
    elif survivor_class == "Cleric":
        stats["spirit"] += 3
        stats["mind"] += 1
    elif survivor_class == "Mage":
        stats["mind"] += 3
        stats["spirit"] += 1

    survivor = Hero(
        name=f"{name_prefix} {name_suffix}",
        hero_class=survivor_class,
        age=random.randint(18, 55),
        level=max(1, dungeon.difficulty),
        xp=0,
        stats=stats,
        signing_bonus=0,
        wage_per_year=0,
        contract_years=0,
        specialty=random_specialty_for_class(survivor_class),
        is_temporary_survivor=True,
    )
    survivor.reset_health_for_expedition()

    missing_health = random.randint(5, max(10, survivor.max_health() // 3))
    survivor.current_health = max(1, survivor.max_health() - missing_health)

    return survivor


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
        RoomOption("Survivor", "Find a stranded adventurer who may join for the rest of the dungeon."),
        RoomOption("Elite", "Hard enemy encounter. Better XP and loot than a normal monster room."),
        RoomOption("Camp", "Safe rest. Small healing, no loot, no XP."),
    ]

    return random.sample(possible_rooms, 3)


def choose_room_option(dungeon: Dungeon, room_number: int, party: List[Hero]) -> RoomOption:
    options = generate_room_options(dungeon, room_number)

    print("\n" + "-" * 60)
    print(bold(f"Room {room_number}/{dungeon.room_count}: Choose Your Path"))
    print(info("One year will pass after this room. Wages are paid at year-end."))
    print_party_status(party)

    for message in describe_party_specialties(party):
        print(message)

    for message in party_matchup_summary(party, dungeon.enemy_type):
        print(message)

    for index, option in enumerate(options, start=1):
        extra = ""
        if option.room_type in COMBAT_ROOM_TYPES:
            enemy_power = dungeon.room_enemy_power(room_number, option.room_type)
            chance = estimate_success_chance(party, enemy_power, option.room_type, dungeon.enemy_type_for_room(option.room_type))
            extra = f" | Enemy Power {enemy_power} | Expected Combat Edge {format_success_chance(chance)}"

        print(f"{index}. {option.room_type}: {option.description}{extra}")

    while True:
        choice = input("Choose next room, blank to retreat, or 'exit' to quit: ").strip()

        if is_exit_command(choice):
            exit_game()

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


def queue_bereavement_payment(state: GameState, hero: Hero) -> str:
    state.pending_bereavement_payments.append(BereavementPayment(hero.name, hero.wage_per_year))
    return warning(
        f"{hero.name}'s remaining contract is void, but {hero.wage_per_year}g is owed "
        f"as this year's bereavement wage."
    )


def recover_equipment_from_dead_hero(state: GameState, hero: Hero, party_has_survivors: bool) -> List[str]:
    messages = []

    if not hero.equipment:
        return messages

    if not party_has_survivors:
        lost_names = ", ".join(item.name for item in hero.equipment.values())
        hero.equipment.clear()
        messages.append(danger(f"{hero.name}'s equipment was lost in the dungeon: {lost_names}."))
        return messages

    for slot, item in list(hero.equipment.items()):
        if random.random() <= EQUIPMENT_RECOVERY_CHANCE:
            state.inventory.append(item)
            messages.append(success(f"Recovered {hero.name}'s {item.name} from the dungeon."))
        else:
            messages.append(warning(f"{hero.name}'s {item.name} could not be recovered."))
        del hero.equipment[slot]

    return messages


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


def resolve_treasure_room(state: GameState, party: List[Hero], dungeon: Dungeon) -> RoomResolution:
    messages = []
    base_loot = random.randint(dungeon.loot_min, dungeon.loot_max) // max(1, dungeon.room_count - 1)
    room_loot = int(base_loot * treasure_gold_multiplier(party))

    if has_specialty(party, "Treasure Hunter"):
        messages.append(highlight("Treasure Hunter specialty increases treasure gold."))

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
                room_number=1,
            )
        )

    if not party:
        messages.append(danger(f"The party was wiped out. The {room_loot}g treasure is lost in the dungeon."))
        return RoomResolution(messages=messages, loot=0, xp=0, party_wiped=True)

    drop_chance = dungeon.item_drop_chance + item_drop_bonus(party)
    if has_specialty(party, "Seer"):
        messages.append(highlight("Seer specialty improves item discovery chance."))

    if random.random() < drop_chance:
        item = generate_item_drop(dungeon, party)
        state.inventory.append(item)
        messages.append(highlight(f"The party found an item: {item.display()}"))

    messages.extend(apply_life_cleric_healing(party))
    return RoomResolution(messages=messages, loot=room_loot, xp=room_xp)


def resolve_shrine_room(party: List[Hero], dungeon: Dungeon) -> RoomResolution:
    messages = [highlight("The party discovers a forgotten shrine.")]
    heal_amount = 12 + (dungeon.difficulty * 4)

    for hero in party:
        messages.append(success(hero.heal(heal_amount)))

    messages.extend(apply_life_cleric_healing(party))
    return RoomResolution(messages=messages, loot=0, xp=0)


def resolve_camp_room(party: List[Hero], dungeon: Dungeon) -> RoomResolution:
    messages = [success("The party finds a defensible camp and takes time to recover.")]
    heal_amount = 8 + (dungeon.difficulty * 2)

    for hero in party:
        messages.append(success(hero.heal(heal_amount)))

    messages.extend(apply_life_cleric_healing(party))
    return RoomResolution(messages=messages, loot=0, xp=0)


def resolve_survivor_room(party: List[Hero], dungeon: Dungeon) -> RoomResolution:
    survivor = create_survivor(dungeon)
    party.append(survivor)

    messages = [
        highlight("The party finds a stranded survivor hiding among the ruins."),
        success(f"{survivor.name}, a {survivor.hero_class} {survivor.specialty}, joins for the rest of the dungeon."),
        info(f"{survivor.name} requires no wages and will leave after the expedition."),
        info(f"Survivor Status: {survivor.display_short()}"),
    ]

    messages.extend(apply_life_cleric_healing(party))
    return RoomResolution(messages=messages, loot=0, xp=0)


def resolve_event_room(state: GameState, party: List[Hero], dungeon: Dungeon) -> RoomResolution:
    messages = [highlight("The party encounters an unknown event.")]
    outcome = random.choice(["gold", "heal", "trap", "item", "survivor", "nothing"])

    if outcome == "gold":
        room_loot = random.randint(dungeon.loot_min // 4, dungeon.loot_max // 3)
        messages.append(success(f"A strange bargain pays off. The party gains {room_loot}g."))
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=room_loot, xp=0)

    if outcome == "heal":
        heal_amount = 10 + dungeon.difficulty * 3
        messages.append(success("A mysterious force restores the party."))
        for hero in party:
            messages.append(success(hero.heal(heal_amount)))
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=0)

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
                room_number=1,
            )
        )

        if not party:
            messages.append(danger("The party was wiped out. Any event rewards are lost."))
            return RoomResolution(messages=messages, loot=0, xp=0, party_wiped=True)

        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=0)

    if outcome == "item":
        item = generate_item_drop(dungeon, party)
        state.inventory.append(item)
        messages.append(highlight(f"The party discovers an item: {item.display()}"))
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=0)

    if outcome == "survivor":
        return resolve_survivor_room(party, dungeon)

    messages.append(info("Nothing happens, which may be a blessing in this place."))
    messages.extend(apply_life_cleric_healing(party))
    return RoomResolution(messages=messages, loot=0, xp=0)


def resolve_room(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    room_number: int,
    room_option: RoomOption,
) -> RoomResolution:
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

    if room_option.room_type == "Survivor":
        return resolve_survivor_room(party, dungeon)

    return RoomResolution(messages=[warning("The party turns back.")], loot=0, xp=0)


def remove_temporary_survivors_from_party(state: GameState, party: List[Hero]) -> List[str]:
    messages = []
    for hero in list(party):
        if hero.is_temporary_survivor:
            party.remove(hero)
            if hero.current_health and hero.current_health > 0:
                messages.append(info(f"{hero.name} parts ways with the guild after the expedition."))
                messages.extend(reputation_for_survivor_rescued(state.reputation))
    return messages


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

        resolution = resolve_room(
            state=state,
            party=party,
            dungeon=dungeon,
            room_number=room_number,
            room_option=room_option,
        )

        room_messages.extend(resolution.messages)
        rooms_completed += 1

        if resolution.party_wiped:
            room_messages.append(danger("Room rewards were not recovered because no heroes escaped."))
        else:
            loot_earned += resolution.loot
            xp_earned += resolution.xp
            state.gold += resolution.loot
            room_messages.append(success(f"Gold after recovered room loot: {state.gold}g."))

        year_messages = advance_one_year_after_room(state, party, room_number)
        room_messages.extend(year_messages)

        expedition_summary.extend(room_messages)
        print_room_result(room_messages, party)

        if not party:
            expedition_summary.append(danger("The expedition ends because the entire party is gone."))
            break

    expedition_summary.append(success(f"Total recovered expedition loot: {loot_earned}g."))
    expedition_summary.append(info(f"Total recovered combat XP: {xp_earned}."))

    if rooms_completed == dungeon.room_count and party:
        expedition_summary.append(success("The dungeon route was completed!"))

    for hero in list(party):
        if hero.is_temporary_survivor:
            continue

        old_level = hero.level
        xp_messages = hero.add_xp(xp_earned)

        for message in xp_messages:
            expedition_summary.append(info(message))

        if hero.level > old_level:
            for _ in range(hero.level - old_level):
                expedition_summary.extend(reputation_for_level_up(state.reputation, hero.hero_class))

        hero.current_health = None

    expedition_summary.extend(remove_temporary_survivors_from_party(state, party))

    return expedition_summary


def finish_expedition(state: GameState, dungeon: Dungeon) -> List[str]:
    messages = [bold("=== Expedition Cleanup ===")]

    state.expedition += 1
    refresh_contract_market(state)

    messages.append(info("Time, wages, contracts, injuries, and retirement were processed room-by-room."))
    return messages
