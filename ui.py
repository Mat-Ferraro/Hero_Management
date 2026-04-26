import os
import sys


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"


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


def format_health_status(status: str) -> str:
    normalized = status.upper()

    if normalized == "DEAD":
        return danger(status)
    if normalized == "CRITICAL":
        return danger(status)
    if normalized == "WOUNDED":
        return warning(status)
    if normalized == "HURT":
        return warning(status)

    return success(status)


enable_windows_ansi_colors()