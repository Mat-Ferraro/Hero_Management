import json
from pathlib import Path
from typing import Dict, List

from game_state import BereavementPayment, GameState
from manager_reputation import ManagerReputation
from models import Dungeon, Hero, Item


SAVE_DIR = Path("saves")
DEFAULT_SAVE_PATH = SAVE_DIR / "save_slot_1.json"


def item_to_dict(item: Item) -> Dict:
    return {
        "name": item.name,
        "slot": item.slot,
        "stat_bonuses": item.stat_bonuses,
        "value": item.value,
    }


def item_from_dict(data: Dict) -> Item:
    return Item(
        name=data["name"],
        slot=data["slot"],
        stat_bonuses=dict(data["stat_bonuses"]),
        value=int(data["value"]),
    )


def hero_to_dict(hero: Hero) -> Dict:
    return {
        "name": hero.name,
        "hero_class": hero.hero_class,
        "age": hero.age,
        "level": hero.level,
        "xp": hero.xp,
        "stats": hero.stats,
        "signing_bonus": hero.signing_bonus,
        "wage_per_year": hero.wage_per_year,
        "contract_years": hero.contract_years,
        "specialty": hero.specialty,
        "equipment": {slot: item_to_dict(item) for slot, item in hero.equipment.items()},
        "injured_years_remaining": hero.injured_years_remaining,
        "wound_history": hero.wound_history,
        "current_health": hero.current_health,
        "debt": hero.debt,
        "is_temporary_survivor": hero.is_temporary_survivor,
    }


def hero_from_dict(data: Dict) -> Hero:
    hero = Hero(
        name=data["name"],
        hero_class=data["hero_class"],
        age=int(data["age"]),
        level=int(data["level"]),
        xp=int(data["xp"]),
        stats=dict(data["stats"]),
        signing_bonus=int(data["signing_bonus"]),
        wage_per_year=int(data["wage_per_year"]),
        contract_years=int(data["contract_years"]),
        specialty=data.get("specialty", "Adventurer"),
        equipment={slot: item_from_dict(item_data) for slot, item_data in data.get("equipment", {}).items()},
        injured_years_remaining=int(data.get("injured_years_remaining", 0)),
        wound_history=list(data.get("wound_history", [])),
        current_health=data.get("current_health"),
        debt=int(data.get("debt", 0)),
        is_temporary_survivor=bool(data.get("is_temporary_survivor", False)),
    )
    return hero


def dungeon_to_dict(dungeon: Dungeon) -> Dict:
    return {
        "name": dungeon.name,
        "difficulty": dungeon.difficulty,
        "years_to_complete": dungeon.years_to_complete,
        "stages": dungeon.stages,
        "enemy_power": dungeon.enemy_power,
        "loot_min": dungeon.loot_min,
        "loot_max": dungeon.loot_max,
        "xp_reward": dungeon.xp_reward,
        "minor_wound_chance": dungeon.minor_wound_chance,
        "mortal_wound_chance": dungeon.mortal_wound_chance,
        "death_chance": dungeon.death_chance,
        "item_drop_chance": dungeon.item_drop_chance,
    }


def dungeon_from_dict(data: Dict) -> Dungeon:
    return Dungeon(
        name=data["name"],
        difficulty=int(data["difficulty"]),
        years_to_complete=int(data["years_to_complete"]),
        stages=int(data.get("stages", data["years_to_complete"])),
        enemy_power=int(data["enemy_power"]),
        loot_min=int(data["loot_min"]),
        loot_max=int(data["loot_max"]),
        xp_reward=int(data["xp_reward"]),
        minor_wound_chance=float(data["minor_wound_chance"]),
        mortal_wound_chance=float(data["mortal_wound_chance"]),
        death_chance=float(data["death_chance"]),
        item_drop_chance=float(data["item_drop_chance"]),
    )


def reputation_to_dict(reputation: ManagerReputation) -> Dict:
    return {
        "overall": reputation.overall,
        "reliability": reputation.reliability,
        "safety": reputation.safety,
        "development": reputation.development,
        "protector": reputation.protector,
        "warrior": reputation.warrior,
        "rogue": reputation.rogue,
        "cleric": reputation.cleric,
        "mage": reputation.mage,
        "history": reputation.history,
    }


def reputation_from_dict(data: Dict) -> ManagerReputation:
    return ManagerReputation(
        overall=int(data.get("overall", 0)),
        reliability=int(data.get("reliability", 0)),
        safety=int(data.get("safety", 0)),
        development=int(data.get("development", 0)),
        protector=int(data.get("protector", 0)),
        warrior=int(data.get("warrior", 0)),
        rogue=int(data.get("rogue", 0)),
        cleric=int(data.get("cleric", 0)),
        mage=int(data.get("mage", 0)),
        history=list(data.get("history", [])),
    )


def bereavement_to_dict(payment: BereavementPayment) -> Dict:
    return {
        "hero_name": payment.hero_name,
        "amount": payment.amount,
    }


def bereavement_from_dict(data: Dict) -> BereavementPayment:
    return BereavementPayment(
        hero_name=data["hero_name"],
        amount=int(data["amount"]),
    )


def game_state_to_dict(state: GameState) -> Dict:
    return {
        "version": 1,
        "expedition": state.expedition,
        "year": state.year,
        "gold": state.gold,
        "roster": [hero_to_dict(hero) for hero in state.roster],
        "available_contracts": [hero_to_dict(hero) for hero in state.available_contracts],
        "inventory": [item_to_dict(item) for item in state.inventory],
        "dungeons": [dungeon_to_dict(dungeon) for dungeon in state.dungeons],
        "retired_heroes": [hero_to_dict(hero) for hero in state.retired_heroes],
        "fallen_heroes": [hero_to_dict(hero) for hero in state.fallen_heroes],
        "reputation": reputation_to_dict(state.reputation),
        "pending_bereavement_payments": [
            bereavement_to_dict(payment) for payment in state.pending_bereavement_payments
        ],
    }


def game_state_from_dict(data: Dict) -> GameState:
    return GameState(
        expedition=int(data["expedition"]),
        year=int(data["year"]),
        gold=int(data["gold"]),
        roster=[hero_from_dict(hero_data) for hero_data in data.get("roster", [])],
        available_contracts=[
            hero_from_dict(hero_data) for hero_data in data.get("available_contracts", [])
        ],
        inventory=[item_from_dict(item_data) for item_data in data.get("inventory", [])],
        dungeons=[dungeon_from_dict(dungeon_data) for dungeon_data in data.get("dungeons", [])],
        retired_heroes=[hero_from_dict(hero_data) for hero_data in data.get("retired_heroes", [])],
        fallen_heroes=[hero_from_dict(hero_data) for hero_data in data.get("fallen_heroes", [])],
        reputation=reputation_from_dict(data.get("reputation", {})),
        pending_bereavement_payments=[
            bereavement_from_dict(payment_data)
            for payment_data in data.get("pending_bereavement_payments", [])
        ],
    )


def save_game(state: GameState, path: Path = DEFAULT_SAVE_PATH) -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    data = game_state_to_dict(state)

    with path.open("w", encoding="utf-8") as save_file:
        json.dump(data, save_file, indent=2)

    return path


def load_game(path: Path = DEFAULT_SAVE_PATH) -> GameState:
    if not path.exists():
        raise FileNotFoundError(f"No save file found at {path}")

    with path.open("r", encoding="utf-8") as save_file:
        data = json.load(save_file)

    return game_state_from_dict(data)


def save_exists(path: Path = DEFAULT_SAVE_PATH) -> bool:
    return path.exists()
