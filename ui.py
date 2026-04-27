import os


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    WHITE = "\033[97m"
    DIM = "\033[2m"


def enable_windows_ansi_colors() -> None:
    if os.name != "nt":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def color_text(text: str, color: str) -> str:
    return f"{color}{text}{Color.RESET}"


def pad_col(text: str, width: int, color: str | None = None, align: str = "left") -> str:
    raw = str(text)

    if len(raw) > width:
        if width <= 1:
            raw = raw[:width]
        else:
            raw = raw[: width - 1] + "…"

    if align == "right":
        padded = raw.rjust(width)
    else:
        padded = raw.ljust(width)

    if color:
        return color_text(padded, color)

    return padded


def success(text: str) -> str:
    return color_text(text, Color.GREEN)


def warning(text: str) -> str:
    return color_text(text, Color.YELLOW)


def danger(text: str) -> str:
    return color_text(text, Color.RED)


def info(text: str) -> str:
    return color_text(text, Color.CYAN)


def highlight(text: str) -> str:
    return color_text(text, Color.MAGENTA)


def bold(text: str) -> str:
    return color_text(text, Color.BOLD)


def dim(text: str) -> str:
    return color_text(text, Color.DIM)


def color_class(hero_class: str) -> str:
    class_colors = {
        "Warrior": Color.RED,
        "Rogue": Color.GREEN,
        "Cleric": Color.CYAN,
        "Mage": Color.MAGENTA,
    }
    return color_text(hero_class, class_colors.get(hero_class, Color.WHITE))


def color_damage_type(damage_type: str) -> str:
    damage_colors = {
        "Physical": Color.YELLOW,
        "Magic": Color.MAGENTA,
        "Holy": Color.CYAN,
    }
    return color_text(damage_type, damage_colors.get(damage_type, Color.WHITE))


def color_growth_rate(growth_rate: str) -> str:
    growth_colors = {
        "Mundane": Color.DIM,
        "Talented": Color.WHITE,
        "Gifted": Color.GREEN,
        "Heroic": Color.CYAN,
        "Legendary": Color.MAGENTA,
        "Mythic": Color.RED,
    }
    return color_text(growth_rate, growth_colors.get(growth_rate, Color.WHITE))


def color_contract_attitude(contract_attitude: str) -> str:
    attitude_colors = {
        "Modest": Color.GREEN,
        "Practical": Color.WHITE,
        "Ambitious": Color.YELLOW,
        "Mercenary": Color.RED,
        "Noble": Color.CYAN,
    }
    return color_text(contract_attitude, attitude_colors.get(contract_attitude, Color.WHITE))


def color_health_status(status: str) -> str:
    if status in ("DEAD", "CRITICAL"):
        return danger(status)

    if status in ("WOUNDED", "HURT"):
        return warning(status)

    return success(status)


def color_money_value(amount: int, low: int = 100, high: int = 300) -> str:
    text = f"{amount}g"

    if amount >= high:
        return danger(text)

    if amount >= low:
        return warning(text)

    return success(text)


enable_windows_ansi_colors()
