"""
Protocol handling for Blackjack game messages.
Handles encoding and decoding of all message types.
"""

import struct
from constants import (
    MAGIC_COOKIE, MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD,
    NAME_LENGTH, ACTION_HIT, ACTION_STAND, RANK_NAMES, SUITS
)


def pad_name(name):
    """
    Pad or truncate a name to exactly NAME_LENGTH bytes.
    Shorter names are padded with null bytes, longer names are truncated.
    """
    name_bytes = name.encode('utf-8')[:NAME_LENGTH]
    return name_bytes.ljust(NAME_LENGTH, b'\x00')


def unpad_name(name_bytes):
    """
    Remove null byte padding from a name.
    """
    return name_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')


# ============== OFFER MESSAGE ==============
# Format: Magic (4) + Type (1) + TCP Port (2) + Server Name (32) = 39 bytes
OFFER_FORMAT = '>I B H 32s'
OFFER_SIZE = struct.calcsize(OFFER_FORMAT)


def pack_offer(tcp_port, server_name):
    """
    Pack an offer message to be sent via UDP broadcast.
    
    Args:
        tcp_port: The TCP port the server is listening on
        server_name: The name of the server/team
    
    Returns:
        bytes: The packed offer message
    """
    return struct.pack(
        OFFER_FORMAT,
        MAGIC_COOKIE,
        MSG_TYPE_OFFER,
        tcp_port,
        pad_name(server_name)
    )


def unpack_offer(data):
    """
    Unpack an offer message received via UDP.
    
    Args:
        data: Raw bytes received
    
    Returns:
        tuple: (tcp_port, server_name) or None if invalid
    """
    if len(data) < OFFER_SIZE:
        return None
    
    try:
        magic, msg_type, tcp_port, name_bytes = struct.unpack(OFFER_FORMAT, data[:OFFER_SIZE])
        
        if magic != MAGIC_COOKIE:
            return None
        if msg_type != MSG_TYPE_OFFER:
            return None
        
        return (tcp_port, unpad_name(name_bytes))
    except struct.error:
        return None


# ============== REQUEST MESSAGE ==============
# Format: Magic (4) + Type (1) + Rounds (1) + Client Name (32) = 38 bytes
REQUEST_FORMAT = '>I B B 32s'
REQUEST_SIZE = struct.calcsize(REQUEST_FORMAT)


def pack_request(num_rounds, client_name):
    """
    Pack a request message to be sent via TCP.
    
    Args:
        num_rounds: Number of rounds to play (1-255)
        client_name: The name of the client/team
    
    Returns:
        bytes: The packed request message
    """
    return struct.pack(
        REQUEST_FORMAT,
        MAGIC_COOKIE,
        MSG_TYPE_REQUEST,
        num_rounds,
        pad_name(client_name)
    )


def unpack_request(data):
    """
    Unpack a request message received via TCP.
    
    Args:
        data: Raw bytes received
    
    Returns:
        tuple: (num_rounds, client_name) or None if invalid
    """
    if len(data) < REQUEST_SIZE:
        return None
    
    try:
        magic, msg_type, num_rounds, name_bytes = struct.unpack(REQUEST_FORMAT, data[:REQUEST_SIZE])
        
        if magic != MAGIC_COOKIE:
            return None
        if msg_type != MSG_TYPE_REQUEST:
            return None
        
        return (num_rounds, unpad_name(name_bytes))
    except struct.error:
        return None


# ============== PAYLOAD MESSAGE ==============
# Client format: Magic (4) + Type (1) + Decision (5) = 10 bytes
# Server format: Magic (4) + Type (1) + Result (1) + Card (3) = 9 bytes

CLIENT_PAYLOAD_FORMAT = '>I B 5s'
CLIENT_PAYLOAD_SIZE = struct.calcsize(CLIENT_PAYLOAD_FORMAT)

SERVER_PAYLOAD_FORMAT = '>I B B 2s 1s'
SERVER_PAYLOAD_SIZE = struct.calcsize(SERVER_PAYLOAD_FORMAT)


def pack_client_payload(action):
    """
    Pack a client payload message (Hit or Stand).
    
    Args:
        action: Either "hit" or "stand"
    
    Returns:
        bytes: The packed payload message
    """
    action_bytes = ACTION_HIT if action.lower() == "hit" else ACTION_STAND
    return struct.pack(
        CLIENT_PAYLOAD_FORMAT,
        MAGIC_COOKIE,
        MSG_TYPE_PAYLOAD,
        action_bytes
    )


def unpack_client_payload(data):
    """
    Unpack a client payload message.
    
    Args:
        data: Raw bytes received
    
    Returns:
        str: "hit" or "stand" or None if invalid
    """
    if len(data) < CLIENT_PAYLOAD_SIZE:
        return None
    
    try:
        magic, msg_type, action_bytes = struct.unpack(CLIENT_PAYLOAD_FORMAT, data[:CLIENT_PAYLOAD_SIZE])
        
        if magic != MAGIC_COOKIE:
            return None
        if msg_type != MSG_TYPE_PAYLOAD:
            return None
        
        if action_bytes == ACTION_HIT:
            return "hit"
        elif action_bytes == ACTION_STAND:
            return "stand"
        else:
            return None
    except struct.error:
        return None


def pack_server_payload(result, card_rank, card_suit):
    """
    Pack a server payload message.
    
    Args:
        result: Game result code (0-3)
        card_rank: Card rank (1-13, or 0 for no card)
        card_suit: Suit index (0-3) or suit character
    
    Returns:
        bytes: The packed payload message
    """
    # Encode rank as 2-digit string
    rank_str = f"{card_rank:02d}".encode('ascii')
    
    # Encode suit as single character
    if isinstance(card_suit, int):
        suit_char = SUITS[card_suit].encode('ascii')
    else:
        suit_char = card_suit.encode('ascii')
    
    return struct.pack(
        SERVER_PAYLOAD_FORMAT,
        MAGIC_COOKIE,
        MSG_TYPE_PAYLOAD,
        result,
        rank_str,
        suit_char
    )


def unpack_server_payload(data):
    """
    Unpack a server payload message.
    
    Args:
        data: Raw bytes received
    
    Returns:
        tuple: (result, card_rank, card_suit) or None if invalid
    """
    if len(data) < SERVER_PAYLOAD_SIZE:
        return None
    
    try:
        magic, msg_type, result, rank_bytes, suit_byte = struct.unpack(
            SERVER_PAYLOAD_FORMAT, data[:SERVER_PAYLOAD_SIZE]
        )
        
        if magic != MAGIC_COOKIE:
            return None
        if msg_type != MSG_TYPE_PAYLOAD:
            return None
        
        card_rank = int(rank_bytes.decode('ascii'))
        card_suit = suit_byte.decode('ascii')
        
        return (result, card_rank, card_suit)
    except (struct.error, ValueError):
        return None


def card_to_string(rank, suit):
    """
    Convert a card rank and suit to a visual colored string.
    
    Args:
        rank: Card rank (1-13)
        suit: Card suit character or index
    
    Returns:
        str: Visual card representation with color
    """
    from constants import SUIT_SYMBOLS, RED, WHITE, RESET, RANK_NAMES, SUITS
    
    if isinstance(suit, int):
        suit = SUITS[suit]
    
    rank_name = RANK_NAMES.get(rank, str(rank))
    symbol = SUIT_SYMBOLS.get(suit, suit)
    
    # Red for hearts and diamonds, white for clubs and spades
    if suit in ['H', 'D']:
        color = RED
    else:
        color = WHITE
    
    return f"{color}[{rank_name}{symbol}]{RESET}"
