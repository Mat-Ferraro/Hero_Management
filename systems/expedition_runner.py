from typing import List

from game_state import GameState, refresh_contract_market
from manager_reputation import reputation_for_level_up
from models import Dungeon, Hero
from .room_system import choose_room_option, print_room_result, resolve_room
from .survivor_system import remove_temporary_survivors_from_party
from .wage_system import advance_one_year_after_room
from ui import bold, danger, info, success, warning


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

