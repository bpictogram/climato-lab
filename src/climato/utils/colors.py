import sys

USE_COLORS = sys.stdout.isatty()
USE_COLORS = True


class Color:
    BLACK = '\033[30m' if USE_COLORS else ""
    RED = '\033[31m' if USE_COLORS else ""
    GREEN = '\033[32m' if USE_COLORS else ""
    YELLOW = '\033[33m' if USE_COLORS else ""  # orange on some systems
    BLUE = '\033[34m' if USE_COLORS else ""
    MAGENTA = '\033[35m' if USE_COLORS else ""
    CYAN = '\033[36m' if USE_COLORS else ""
    LIGHT_GRAY = '\033[37m' if USE_COLORS else ""
    DARK_GRAY = '\033[90m' if USE_COLORS else ""
    BRIGHT_RED = '\033[91m' if USE_COLORS else ""
    BRIGHT_GREEN = '\033[92m' if USE_COLORS else ""
    BRIGHT_YELLOW = '\033[93m' if USE_COLORS else ""
    BRIGHT_BLUE = '\033[94m' if USE_COLORS else ""
    BRIGHT_MAGENTA = '\033[95m' if USE_COLORS else ""
    BRIGHT_CYAN = '\033[96m' if USE_COLORS else ""
    WHITE = '\033[97m' if USE_COLORS else ""
    RESET = '\033[0m' if USE_COLORS else ""  # called to return to standard terminal text color
