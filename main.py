import random

from battle_simulator import (
    exit_game,
    finish_expedition,
    is_exit_command,
    prepare_expedition_payroll,
    simulate_multi_stage_dungeon,
)
from game_state import GameState, create_game
from models import CLASS_RULES
from save_system import DEFAULT_SAVE_PATH, load_game, save_exists, save_game
from table_display import (
    print_compact_legacy_hero_table,
    print_dungeon_table,
    print_hero_table,
    print_inventory_table,
)
from ui import danger, success, warning


def print_header(state: GameState) -> None:
    print("\n" + "=" * 70)
    print(f"Hero Management Prototype | Year {state.year} | Expedition {state.expedition} | Gold: {state.gold}g")
    print("=" * 70)


def main_menu() -> None:
    print("\nMain Menu")
    print("1. View roster")
    print("2. View available contracts")
    print("3. Sign hero")
    print("4. View inventory")
    print("5. Equip item")
    print("6. Sell item")
    print("7. Choose dungeon and raid")
    print("8. View retired heroes")
    print("9. View fallen heroes")
    print("10. View class rules")
    print("11. View manager reputation")
    print("12. Save game")
    print("13. Load game")
    print("14. Quit")
    print("\nTip: type 'exit', 'quit', or 'q' at most prompts to close the game.")


def get_choice(prompt: str, minimum: int, maximum: int):
    raw = input(prompt).strip()

    if is_exit_command(raw):
        exit_game()

    if not raw:
        return None

    try:
        value = int(raw)
    except ValueError:
        print(warning("Please enter a number."))
        return None

    if value < minimum or value > maximum:
        print(warning(f"Please enter a number from {minimum} to {maximum}."))
        return None

    return value


def checked_input(prompt: str) -> str:
    raw = input(prompt).strip()
    if is_exit_command(raw):
        exit_game()
    return raw


def view_roster(state: GameState) -> None:
    print("\n=== Roster ===")

    if not state.roster:
        print(warning("No heroes signed yet."))
        return

    print(f"Total wage bill per year: {sum(hero.wage_per_year for hero in state.roster)}g")
    print(f"Total outstanding debt: {sum(hero.debt for hero in state.roster)}g")
    print(f"Pending bereavement payments: {sum(payment.amount for payment in state.pending_bereavement_payments)}g")
    print_hero_table(state.roster, include_money=False)


def view_contracts(state: GameState) -> None:
    print("\n=== Available Contracts ===")

    if not state.available_contracts:
        print(warning("No available contracts."))
        return

    print_hero_table(state.available_contracts, include_money=True)


def sign_hero(state: GameState) -> None:
    view_contracts(state)

    if not state.available_contracts:
        return

    choice = get_choice("\nSign which hero? Enter number or blank to cancel: ", 1, len(state.available_contracts))
    if choice is None:
        return

    hero = state.available_contracts[choice - 1]

    if state.gold < hero.signing_bonus:
        print(danger(f"Not enough gold. Need {hero.signing_bonus}g for the signing bonus."))
        return

    state.gold -= hero.signing_bonus
    state.roster.append(hero)
    state.available_contracts.pop(choice - 1)

    print(success(f"Signed {hero.name}. Paid {hero.signing_bonus}g. Wage: {hero.wage_per_year}g/year."))


def view_inventory(state: GameState) -> None:
    print("\n=== Inventory ===")

    if not state.inventory:
        print(warning("No items yet."))
        return

    print_inventory_table(state.inventory)


def equip_item(state: GameState) -> None:
    if not state.roster:
        print(warning("You need heroes before equipping items."))
        return

    if not state.inventory:
        print(warning("No items to equip."))
        return

    view_inventory(state)
    item_choice = get_choice("\nChoose item to equip or blank to cancel: ", 1, len(state.inventory))
    if item_choice is None:
        return

    item = state.inventory[item_choice - 1]

    print("\nChoose hero:")
    print_hero_table(state.roster, include_money=False)

    hero_choice = get_choice("Hero number or blank to cancel: ", 1, len(state.roster))
    if hero_choice is None:
        return

    hero = state.roster[hero_choice - 1]

    if not item.can_equip(hero.hero_class):
        allowed = ", ".join(item.class_restrictions)
        print(danger(f"{hero.name} cannot equip {item.name}. Allowed classes: {allowed}."))
        return

    old_item = hero.equipment.get(item.slot)
    hero.equipment[item.slot] = item
    state.inventory.pop(item_choice - 1)

    if old_item:
        state.inventory.append(old_item)
        print(success(f"Equipped {item.name} to {hero.name}. Returned {old_item.name} to inventory."))
    else:
        print(success(f"Equipped {item.name} to {hero.name}."))


def sell_item(state: GameState) -> None:
    if not state.inventory:
        print(warning("No items to sell."))
        return

    view_inventory(state)
    item_choice = get_choice("\nChoose item to sell or blank to cancel: ", 1, len(state.inventory))
    if item_choice is None:
        return

    item = state.inventory[item_choice - 1]
    sell_value = max(1, item.value)
    confirm = checked_input(f"Sell {item.name} for {sell_value}g? [y/N]: ").lower()

    if confirm != "y":
        return

    state.inventory.pop(item_choice - 1)
    state.gold += sell_value
    print(success(f"Sold {item.name} for {sell_value}g."))


def choose_dungeon_and_raid(state: GameState) -> None:
    if not state.roster:
        print(warning("You need to sign heroes before raiding dungeons."))
        return

    total_debt = sum(hero.debt for hero in state.roster)
    total_wage_per_year = sum(hero.wage_per_year for hero in state.roster)
    total_bereavement = sum(payment.amount for payment in state.pending_bereavement_payments)

    print("\nBefore each expedition:")
    print("- Any outstanding hero debt must be cleared before entering.")
    print("- Wages are paid after each dungeon room, because each room equals one year.")
    print("- If yearly wages cannot be paid, they become debt.")
    print(f"\nCurrent wage bill per year: {total_wage_per_year}g. Current gold: {state.gold}g.")
    print(f"Current outstanding debt: {total_debt}g.")
    print(f"Pending bereavement payments: {total_bereavement}g.")

    print("\n=== Dungeons ===")
    print_dungeon_table(state.dungeons, total_debt=total_debt, wage_per_year=total_wage_per_year)

    dungeon_choice = get_choice("\nChoose dungeon or blank to cancel: ", 1, len(state.dungeons))
    if dungeon_choice is None:
        return

    dungeon = state.dungeons[dungeon_choice - 1]

    projected_full_wages = total_wage_per_year * dungeon.room_count
    if projected_full_wages > state.gold:
        print(
            warning(
                "\nWARNING: You cannot currently afford the full projected wage cost "
                "for this dungeon route. Unpaid year-end wages may become debt."
            )
        )
        proceed = checked_input("Proceed anyway? [y/N]: ").lower()
        if proceed != "y":
            return

    print("\n".join(prepare_expedition_payroll(state)))

    available_heroes = [hero for hero in state.roster if hero.injured_years_remaining <= 0]
    if not available_heroes:
        print(danger("No available heroes can raid after debt/injuries are resolved."))
        return

    print("\nAvailable heroes:")
    print_hero_table(available_heroes, include_money=False)

    print("\nEnter up to 4 hero numbers separated by commas. Example: 1,2,3")
    raw_party = checked_input("Party: ")
    if not raw_party:
        return

    try:
        selected_indexes = [int(value.strip()) for value in raw_party.split(",") if value.strip()]
    except ValueError:
        print(danger("Invalid party selection."))
        return

    if not selected_indexes or len(selected_indexes) > 4 or len(set(selected_indexes)) != len(selected_indexes):
        print(warning("Party must include 1 to 4 unique heroes."))
        return

    party = []
    for index in selected_indexes:
        if index < 1 or index > len(available_heroes):
            print(danger("Invalid hero number."))
            return
        party.append(available_heroes[index - 1])

    print("\n".join(simulate_multi_stage_dungeon(state, party, dungeon)))
    print("\n".join(finish_expedition(state, dungeon)))


def view_retired_heroes(state: GameState) -> None:
    print("\n=== Retired Heroes ===")

    if not state.retired_heroes:
        print(warning("No retired heroes yet."))
        return

    print_compact_legacy_hero_table(state.retired_heroes, label="Retired")


def view_fallen_heroes(state: GameState) -> None:
    print("\n=== Fallen Heroes ===")

    if not state.fallen_heroes:
        print(warning("No fallen heroes yet."))
        return

    print_compact_legacy_hero_table(state.fallen_heroes, label="Fallen")


def view_class_rules() -> None:
    print("\n=== Class Rules ===")

    for class_name, rules in CLASS_RULES.items():
        print(f"\n{class_name}")
        print(f"  {rules['description']}")
        print(f"  Young until: {rules['young_until']}")
        print(f"  Prime until: {rules['prime_until']}")
        print(f"  Retirement risk starts after age: {rules['retirement_age']}")

        if rules["old_decline_stat"]:
            print(f"  Declines after prime: {rules['old_decline_stat']}")
        else:
            print("  No automatic age decline in this prototype.")


def view_manager_reputation(state: GameState) -> None:
    print("\n" + state.reputation.display())


def save_current_game(state: GameState) -> None:
    path = save_game(state)
    print(success(f"Game saved to {path}."))


def load_saved_game() -> GameState | None:
    if not save_exists():
        print(warning(f"No save file found at {DEFAULT_SAVE_PATH}."))
        return None

    confirm = checked_input(f"Load save from {DEFAULT_SAVE_PATH}? Current unsaved progress will be lost. [y/N]: ").lower()
    if confirm != "y":
        return None

    try:
        state = load_game()
    except Exception as exc:
        print(danger(f"Failed to load save: {exc}"))
        return None

    print(success(f"Loaded save from {DEFAULT_SAVE_PATH}."))
    return state


def run_game() -> None:
    random.seed()
    state = create_game()

    print("Hero Management Autobattler Prototype")
    print("Recruit heroes, raid dungeons, earn loot, and build your guild.")

    while True:
        print_header(state)
        main_menu()

        choice = get_choice("Choose an action: ", 1, 14)
        if choice is None:
            continue

        if choice == 1:
            view_roster(state)
        elif choice == 2:
            view_contracts(state)
        elif choice == 3:
            sign_hero(state)
        elif choice == 4:
            view_inventory(state)
        elif choice == 5:
            equip_item(state)
        elif choice == 6:
            sell_item(state)
        elif choice == 7:
            choose_dungeon_and_raid(state)
        elif choice == 8:
            view_retired_heroes(state)
        elif choice == 9:
            view_fallen_heroes(state)
        elif choice == 10:
            view_class_rules()
        elif choice == 11:
            view_manager_reputation(state)
        elif choice == 12:
            save_current_game(state)
        elif choice == 13:
            loaded_state = load_saved_game()
            if loaded_state is not None:
                state = loaded_state
        elif choice == 14:
            print(success("Thanks for playing."))
            break


if __name__ == "__main__":
    run_game()
