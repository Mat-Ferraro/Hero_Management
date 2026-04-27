from combat_types import party_matchup_summary
import random
from typing import List

from event_system import apply_event_reputation, choose_event_choice, choose_event_for_enemy, describe_event_choice, print_event_choices
from game_state import GameState
from hero_specialties import apply_life_cleric_healing, describe_party_specialties, has_specialty, item_drop_bonus, treasure_gold_multiplier
from manager_reputation import reputation_for_wound
from models import Dungeon, Hero
from .combat_system import apply_room_damage_and_casualties, estimate_success_chance, resolve_combat_room
from .loot_system import generate_item_drop
from .room_resolution import RoomOption, RoomResolution
from .shared import exit_game, format_success_chance, is_exit_command, print_party_status
from .survivor_system import resolve_survivor_room
from ui import bold, danger, highlight, info, success, warning


COMBAT_ROOM_TYPES = {"Monster", "Elite", "Boss"}


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

def resolve_event_room(state: GameState, party: List[Hero], dungeon: Dungeon) -> RoomResolution:
    event = choose_event_for_enemy(dungeon.enemy_type)
    print_event_choices(event)

    choice = choose_event_choice(event, is_exit_command, exit_game)
    outcome = choice.get("outcome", "nothing")
    messages = [
        highlight(f"Event: {event.get('name', 'Unknown Event')}"),
        info(describe_event_choice(choice)),
    ]

    messages.extend(
        apply_event_reputation(
            state=state,
            reputation_changes=choice.get("reputation", {}),
            reason=f"Event choice: {event.get('name', 'Unknown Event')}",
        )
    )

    if outcome == "survivor":
        survivor_resolution = resolve_survivor_room(party, dungeon)
        messages.extend(survivor_resolution.messages)
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=0)

    if outcome == "heal":
        heal_amount = 12 + dungeon.difficulty * 4
        for hero in party:
            messages.append(success(hero.heal(heal_amount)))
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=0)

    if outcome == "cursed_power":
        bonus_xp = max(5, dungeon.xp_reward // max(2, dungeon.room_count))
        messages.append(info(f"The party gains {bonus_xp} forbidden XP."))
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
            messages.append(danger("The party was wiped out. The forbidden knowledge is lost."))
            return RoomResolution(messages=messages, loot=0, xp=0, party_wiped=True)

        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=bonus_xp)

    if outcome == "item":
        item = generate_item_drop(dungeon, party)
        state.inventory.append(item)
        messages.append(highlight(f"The party recovers an item: {item.display()}"))
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=0)

    if outcome == "trap_and_loot":
        room_loot = random.randint(dungeon.loot_min // 4, dungeon.loot_max // 2)
        messages.append(success(f"The party grabs supplies worth {room_loot}g."))
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
            messages.append(danger(f"The party was wiped out. The {room_loot}g in supplies is lost."))
            return RoomResolution(messages=messages, loot=0, xp=0, party_wiped=True)

        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=room_loot, xp=0)

    if outcome == "loot":
        room_loot = random.randint(dungeon.loot_min // 5, dungeon.loot_max // 3)
        messages.append(success(f"The party gains {room_loot}g in supplies."))
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=room_loot, xp=0)

    if outcome == "xp_and_wound":
        bonus_xp = max(10, dungeon.xp_reward // max(2, dungeon.room_count))
        messages.append(info(f"The party gains {bonus_xp} XP from the bargain."))

        if party:
            target = random.choice(party)
            messages.append(warning(target.apply_minor_wound()))
            messages.extend(reputation_for_wound(state.reputation, target.hero_class, "minor"))

        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=bonus_xp)

    if outcome == "reputation":
        messages.append(success("The party earns goodwill without taking material rewards."))
        messages.extend(apply_life_cleric_healing(party))
        return RoomResolution(messages=messages, loot=0, xp=0)

    messages.append(info("The party moves on without further consequence."))
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

