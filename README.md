# Blackijecky — Multiplayer Network Blackjack (Client/Server)

Intro to Networks 2025/2026 Hackathon Assignment — **Simplified Blackjack** over the network.

This repository implements a fully working **server (dealer)** and **client (player)** in **Python 3**, using:

- **UDP broadcast** for server discovery (offer messages)
- **TCP** for the game session (request + payload messages)
- A **strict binary protocol** (Big-Endian) to ensure interoperability with other teams

---

## Repository Layout

- `server.py` — Dealer: broadcasts offers over UDP and serves games over TCP (multi-client via threads). fileciteturn0file0  
- `client.py` — Player: listens for offers, connects via TCP, plays rounds, and prints UI/stats. fileciteturn0file1  
- `protocol.py` — Binary protocol: packing/unpacking, fixed sizes, validation utilities. fileciteturn0file3  
- `constants.py` — Shared constants: ports, magic cookie, message types, result codes, colors, helpers. fileciteturn0file2  

---

## Requirements

- Python **3.x**
- No external dependencies (standard library only)

---

## Quick Start

### 1) Run the Server (Dealer)

```bash
python/py server.py
```

The server will:

- Bind to an **ephemeral TCP port** (chosen automatically)
- Broadcast **UDP offers** every second on UDP port **13122**
- Accept incoming TCP connections and run the requested number of rounds

### 2) Run the Client (Player)

```bash
python/py client.py
```

The client will:

- Listen on UDP port **13122** for offer broadcasts
- Connect to the first valid offer received
- Ask how many rounds to play (1–255)
- Play the session using interactive input (`Hit` / `Stand`)

---

## Game Rules (Simplified Blackjack)

- Standard **52-card deck**
- Card values:
  - 2–10 → face value
  - J/Q/K → 10
  - A → 11 (**always 11**)
- No special blackjack rule, no betting, no splitting

### Round Flow

1. **Initial deal**
   - Player gets 2 cards face-up
   - Dealer gets 2 cards:
     - first card is visible to the player
     - second card is hidden until dealer’s turn
2. **Player turn**
   - Player chooses repeatedly:
     - `Hit` (ask for another card)
     - `Stand` (stop taking cards)
   - If player sum > 21 → **player busts** and immediately loses the round
3. **Dealer turn** (only if player didn’t bust)
   - Dealer reveals hidden card
   - Dealer hits until:
     - sum ≥ 17 → stand
     - sum > 21 → dealer busts
4. **Winner**
   - Player busts → dealer wins
   - Dealer busts → player wins
   - Otherwise compare totals:
     - higher total wins
     - equal totals → tie

---

## Network Protocol Specification

All protocol messages start with the **magic cookie**:

- Magic Cookie (4 bytes): `0xabcddcba`

Byte order: **Big-Endian** (network byte order).

### Message Types

- `0x2` — Offer (UDP) — server → clients
- `0x3` — Request (TCP) — client → server
- `0x4` — Payload (TCP) — both directions

### Fixed Packet Formats

#### 1) Offer (UDP, 39 bytes)

```
[Magic Cookie: 4] [Type: 1] [Server TCP Port: 2] [Server Name: 32]
```

- Server name is fixed-length 32 bytes:
  - if shorter → padded with `0x00`
  - if longer → truncated to 32 bytes

#### 2) Request (TCP, 38 bytes)

```
[Magic Cookie: 4] [Type: 1] [Num Rounds: 1] [Client Name: 32]
```

- `Num Rounds` is 1 byte: 1–255
- Client name is fixed-length 32 bytes (same padding rules)

#### 3) Payload — Client → Server (TCP, 10 bytes)

```
[Magic Cookie: 4] [Type: 1] [Decision: 5]
```

- Decision is exactly **5 ASCII bytes**:
  - `"Hittt"`  (hit)
  - `"Stand"`  (stand)

#### 4) Payload — Server → Client (TCP, 9 bytes)

```
[Magic Cookie: 4] [Type: 1] [Result: 1] [Rank: 2] [Suit: 1]
```

Result codes (1 byte):

- `0x0` — round not over
- `0x1` — tie
- `0x2` — loss (client lost / dealer won)
- `0x3` — win  (client won / dealer lost)

Card encoding:

- Rank: 1–13 (2 bytes)
- Suit: 0–3 (1 byte)

---

## Implementation Notes

- **Server discovery:** UDP broadcast offers every second.
- **Concurrency:** server handles multiple clients via threads.
- **Robustness:** basic validation for magic cookie/type, graceful handling of disconnects/timeouts.
- **Console UI:** client prints round stages and summary statistics (win rate, totals).

---

## Troubleshooting

- If the client can’t bind to UDP port `13122`, close any other clients using the same port and retry.
- In noisy networks/hotspots, make sure both machines are on the same LAN/hotspot and that UDP broadcasts are not blocked.

---

## Authors / Team

- Team name: **Byte the Dealer**

---

## Team members:
- Noam Yehoshua
- Dotan Katz
- Bar Elhayani
