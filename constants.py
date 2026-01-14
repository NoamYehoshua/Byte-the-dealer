"""
Constants for the Blackjack game protocol.
"""

# Network Constants
UDP_BROADCAST_PORT = 13122  # Port for UDP offer broadcasts
MAGIC_COOKIE = 0xabcddcba   # Magic cookie for all messages

# Message Types
MSG_TYPE_OFFER = 0x2        # Server to client offer
MSG_TYPE_REQUEST = 0x3      # Client to server request
MSG_TYPE_PAYLOAD = 0x4      # Game payload (both directions)

# Game Results
RESULT_ROUND_NOT_OVER = 0x0
RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3

# Player Actions (5 bytes each, padded with spaces if needed)
ACTION_HIT = b"Hittt"
ACTION_STAND = b"Stand"

# Name Length
NAME_LENGTH = 32

# Card Suits
SUITS = ['H', 'D', 'C', 'S']  # Hearts, Diamonds, Clubs, Spades
SUIT_NAMES = {'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs', 'S': 'Spades'}

# Card Symbols (Unicode)
SUIT_SYMBOLS = {'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠'}

# ANSI Colors for terminal
RED = '\033[91m'
WHITE = '\033[97m'
RESET = '\033[0m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'


def strip_ansi(text):
    """Remove ANSI color codes from text to get actual display length."""
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)


def pad_line(content, width, border_color, border_char='║'):
    """
    Create a line with proper padding regardless of ANSI codes.
    
    Args:
        content: The text content (may include ANSI codes)
        width: Total width between borders (not including borders)
        border_color: Color for the border
        border_char: Character to use for border
    
    Returns:
        Formatted line with borders
    """
    visible_len = len(strip_ansi(content))
    padding = width - visible_len
    return f"{border_color}{border_char}{RESET}{content}{' ' * padding}{border_color}{border_char}{RESET}"


def make_box(title, lines, width=40, title_color=YELLOW, border_color=GREEN):
    """
    Create a box with title and content lines.
    
    Args:
        title: Title text
        lines: List of content lines
        width: Inner width of the box
        title_color: Color for title
        border_color: Color for borders
    
    Returns:
        Complete box as string
    """
    top = f"{border_color}╔{'═' * width}╗{RESET}"
    title_padded = title.center(width)
    title_line = f"{border_color}║{RESET}{title_color}{BOLD}{title_padded}{RESET}{border_color}║{RESET}"
    separator = f"{border_color}╠{'═' * width}╣{RESET}"
    bottom = f"{border_color}╚{'═' * width}╝{RESET}"
    
    result = [top, title_line, separator]
    for line in lines:
        result.append(pad_line(f" {line}", width, border_color))
    result.append(bottom)
    
    return '\n'.join(result)

# Card Ranks (1-13: Ace through King)
RANK_NAMES = {
    1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
    8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K'
}

# Card Values for Blackjack
def get_card_value(rank):
    """
    Get the blackjack value of a card.
    Ace = 11, Face cards (J, Q, K) = 10, Number cards = their value.
    """
    if rank == 1:  # Ace
        return 11
    elif rank >= 11:  # J, Q, K
        return 10
    else:
        return rank

# Timeouts
OFFER_INTERVAL = 1.0        # Seconds between UDP broadcasts
TCP_TIMEOUT = 30.0          # Timeout for TCP operations (30 seconds for player input)
UDP_TIMEOUT = 10.0          # Timeout for UDP receive

# Team Name
TEAM_NAME = "Byte the Dealer"
