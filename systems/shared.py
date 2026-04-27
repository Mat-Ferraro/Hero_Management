from typing import List

from models import Hero
from ui import danger, success, warning


EXIT_COMMANDS = {"exit", "quit", "q"}


def is_exit_command(raw: str) -> bool:
    return raw.strip().lower() in EXIT_COMMANDS

def exit_game() -> None:
    print("Exiting game.")
    raise SystemExit

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

