from typing import List

from game_state import GameState
from manager_reputation import reputation_for_debt_created, reputation_for_wages_paid
from models import Hero
from ui import bold, danger, success, warning


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

