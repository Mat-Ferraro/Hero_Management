import random

from battle_simulator import finish_expedition, prepare_expedition_payroll, simulate_multi_stage_dungeon
from game_state import GameState, create_game
from models import CLASS_RULES
from ui import danger, warning


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
    print("6. Choose dungeon and raid")
    print("7. View retired heroes")
    print("8. View fallen heroes")
    print("9. View class rules")
    print("10. Quit")


def get_choice(prompt: str, minimum: int, maximum: int):
    raw = input(prompt).strip()
    if not raw:
        return None

    try:
        value = int(raw)
    except ValueError:
        print("Please enter a number.")
        return None

    if value < minimum or value > maximum:
        print(f"Please enter a number from {minimum} to {maximum}.")
        return None

    return value


def view_roster(state: GameState) -> None:
    print("\n=== Roster ===")

    if not state.roster:
        print("No heroes signed yet.")
        return

    print(f"Total wage bill per year: {sum(hero.wage_per_year for hero in state.roster)}g")
    print(f"Total outstanding debt: {sum(hero.debt for hero in state.roster)}g")

    for index, hero in enumerate(state.roster, start=1):
        print(f"\n{index}. {hero.display_full()}")


def view_contracts(state: GameState) -> None:
    print("\n=== Available Contracts ===")

    if not state.available_contracts:
        print("No available contracts.")
        return

    for index, hero in enumerate(state.available_contracts, start=1):
        print(f"{index}. {hero.display_contract()}")


def sign_hero(state: GameState) -> None:
    view_contracts(state)

    if not state.available_contracts:
        return

    choice = get_choice("\nSign which hero? Enter number or blank to cancel: ", 1, len(state.available_contracts))
    if choice is None:
        return

    hero = state.available_contracts[choice - 1]

    if state.gold < hero.signing_bonus:
        print(f"Not enough gold. Need {hero.signing_bonus}g for the signing bonus.")
        return

    state.gold -= hero.signing_bonus
    state.roster.append(hero)
    state.available_contracts.pop(choice - 1)

    print(f"Signed {hero.name}. Paid {hero.signing_bonus}g. Wage: {hero.wage_per_year}g/year.")


def view_inventory(state: GameState) -> None:
    print("\n=== Inventory ===")

    if not state.inventory:
        print("No items yet.")
        return

    for index, item in enumerate(state.inventory, start=1):
        print(f"{index}. {item.display()}")


def equip_item(state: GameState) -> None:
    if not state.roster:
        print("You need heroes before equipping items.")
        return

    if not state.inventory:
        print("No items to equip.")
        return

    view_inventory(state)
    item_choice = get_choice("\nChoose item to equip or blank to cancel: ", 1, len(state.inventory))
    if item_choice is None:
        return

    item = state.inventory[item_choice - 1]

    print("\nChoose hero:")
    for index, hero in enumerate(state.roster, start=1):
        print(f"{index}. {hero.display_short()}")

    hero_choice = get_choice("Hero number or blank to cancel: ", 1, len(state.roster))
    if hero_choice is None:
        return

    hero = state.roster[hero_choice - 1]
    old_item = hero.equipment.get(item.slot)
    hero.equipment[item.slot] = item
    state.inventory.pop(item_choice - 1)

    if old_item:
        state.inventory.append(old_item)
        print(f"Equipped {item.name} to {hero.name}. Returned {old_item.name} to inventory.")
    else:
        print(f"Equipped {item.name} to {hero.name}.")


def choose_dungeon_and_raid(state: GameState) -> None:
    if not state.roster:
        print("You need to sign heroes before raiding dungeons.")
        return

    total_debt = sum(hero.debt for hero in state.roster)
    total_wage_per_year = sum(hero.wage_per_year for hero in state.roster)

    print("\nBefore each expedition:")
    print("- Any outstanding hero debt must be cleared first.")
    print("- Then all active heroes must be paid their first year of wages.")
    print("- Later expedition years are settled after loot is recovered.")
    print(f"\nCurrent wage bill per year: {total_wage_per_year}g. Current gold: {state.gold}g.")
    print(f"Current outstanding debt: {total_debt}g.")

    print("\n=== Dungeons ===")
    for index, dungeon in enumerate(state.dungeons, start=1):
        first_year_required = total_debt + total_wage_per_year
        projected_full_wages = total_wage_per_year * dungeon.years_to_complete
        print(
            f"{index}. {dungeon.display()} | "
            f"Required Before Start: {first_year_required}g | "
            f"Projected Full Wages: {projected_full_wages}g"
        )

    dungeon_choice = get_choice("\nChoose dungeon or blank to cancel: ", 1, len(state.dungeons))
    if dungeon_choice is None:
        return

    dungeon = state.dungeons[dungeon_choice - 1]

    projected_full_wages = total_wage_per_year * dungeon.years_to_complete
    if projected_full_wages > state.gold:
        print(
            warning(
                "\nWARNING: You cannot currently afford the full projected wage cost "
                "for this expedition. Unpaid later-year wages may become debt."
            )
        )
        proceed = input("Proceed anyway? [y/N]: ").strip().lower()
        if proceed != "y":
            return

    print("\n".join(prepare_expedition_payroll(state)))

    available_heroes = [hero for hero in state.roster if hero.injured_years_remaining <= 0]
    if not available_heroes:
        print(danger("No available heroes can raid after payroll/injuries are resolved."))
        return

    print("\nAvailable heroes:")
    for index, hero in enumerate(available_heroes, start=1):
        print(f"{index}. {hero.display_short()}")

    print("\nEnter up to 4 hero numbers separated by commas. Example: 1,2,3")
    raw_party = input("Party: ").strip()
    if not raw_party:
        return

    try:
        selected_indexes = [int(value.strip()) for value in raw_party.split(",") if value.strip()]
    except ValueError:
        print("Invalid party selection.")
        return

    if not selected_indexes or len(selected_indexes) > 4 or len(set(selected_indexes)) != len(selected_indexes):
        print("Party must include 1 to 4 unique heroes.")
        return

    party = []
    for index in selected_indexes:
        if index < 1 or index > len(available_heroes):
            print("Invalid hero number.")
            return
        party.append(available_heroes[index - 1])

    print("\n".join(simulate_multi_stage_dungeon(state, party, dungeon)))
    print("\n".join(finish_expedition(state, dungeon)))


def view_retired_heroes(state: GameState) -> None:
    print("\n=== Retired Heroes ===")

    if not state.retired_heroes:
        print("No retired heroes yet.")
        return

    for index, hero in enumerate(state.retired_heroes, start=1):
        print(f"{index}. {hero.name} | {hero.hero_class} | Retired Age {hero.age} | Lv {hero.level}")


def view_fallen_heroes(state: GameState) -> None:
    print("\n=== Fallen Heroes ===")

    if not state.fallen_heroes:
        print("No fallen heroes yet.")
        return

    for index, hero in enumerate(state.fallen_heroes, start=1):
        print(f"{index}. {hero.name} | {hero.hero_class} | Died Age {hero.age} | Lv {hero.level}")


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


def run_game() -> None:
    random.seed()
    state = create_game()

    print("Hero Management Autobattler Prototype")
    print("Recruit heroes, raid dungeons, earn loot, and build your guild.")

    while True:
        print_header(state)
        main_menu()

        choice = get_choice("Choose an action: ", 1, 10)
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
            choose_dungeon_and_raid(state)
        elif choice == 7:
            view_retired_heroes(state)
        elif choice == 8:
            view_fallen_heroes(state)
        elif choice == 9:
            view_class_rules()
        elif choice == 10:
            print("Thanks for playing.")
            break


if __name__ == "__main__":
    run_game()
