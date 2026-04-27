import random
from typing import Dict, List

from data_loader import load_events
from ui import danger, highlight, info, success, warning


def choose_event_for_enemy(enemy_type: str) -> Dict:
    events = load_events()
    matching_events = [
        event for event in events
        if enemy_type in event.get("enemy_types", []) or not event.get("enemy_types")
    ]

    if not matching_events:
        return {
            "name": "Empty Chamber",
            "description": "The party finds a quiet room and nothing else.",
            "choices": [
                {
                    "label": "Move on",
                    "outcome": "nothing",
                    "reputation": {},
                    "message": "Nothing happens.",
                }
            ],
        }

    return random.choice(matching_events)


def apply_event_reputation(state, reputation_changes: Dict[str, int], reason: str) -> List[str]:
    if not reputation_changes:
        return []

    message = state.reputation.adjust(reason, **reputation_changes)
    return [message] if message else []


def print_event_choices(event: Dict) -> None:
    print("\n" + highlight(f"Event: {event.get('name', 'Unknown Event')}"))
    print(event.get("description", ""))

    for index, choice in enumerate(event.get("choices", []), start=1):
        print(f"{index}. {choice.get('label', 'Unknown choice')}")


def choose_event_choice(event: Dict, is_exit_command, exit_game) -> Dict:
    choices = event.get("choices", [])

    while True:
        raw = input("Choose event response, blank for option 1, or 'exit' to quit: ").strip()

        if is_exit_command(raw):
            exit_game()

        if not raw:
            return choices[0]

        try:
            selected = int(raw)
        except ValueError:
            print("Please enter a valid choice number.")
            continue

        if 1 <= selected <= len(choices):
            return choices[selected - 1]

        print(f"Please choose a number from 1 to {len(choices)}.")


def describe_event_choice(choice: Dict) -> str:
    return choice.get("message", "The party makes a choice.")
