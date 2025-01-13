from colorama import init as colorama_init
from colorama import Fore, Style

COLORS = Fore
colorama_init(autoreset=True)

def print_in_color(text: str, color: Fore = COLORS.RESET):
    print(f"{color}{text}")


def print_error(text: str):
    print_in_color(f"{Style.BRIGHT}{text}", COLORS.RED)