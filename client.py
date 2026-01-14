"""
Blackjack Client - Connects to the server and plays the game.

The client:
1. Listens for UDP offer broadcasts
2. Connects to the first available server via TCP
3. Plays the requested number of rounds
"""

import socket
import struct
import time
from constants import (
    UDP_BROADCAST_PORT, TCP_TIMEOUT, UDP_TIMEOUT,
    RESULT_WIN, RESULT_LOSS, RESULT_TIE, RESULT_ROUND_NOT_OVER,
    TEAM_NAME, get_card_value
)
from protocol import (
    unpack_offer, pack_request, pack_client_payload,
    unpack_server_payload, card_to_string, REQUEST_SIZE, SERVER_PAYLOAD_SIZE
)


class BlackjackClient:
    """
    Client class that connects to a server and plays Blackjack.
    """
    
    def __init__(self, team_name=TEAM_NAME):
        """
        Initialize the client.
        
        Args:
            team_name: Name of the client team
        """
        self.team_name = team_name
        self.running = False
        
        # Game statistics
        self.total_wins = 0
        self.total_losses = 0
        self.total_ties = 0
    
    def listen_for_offers(self):
        """
        Listen for UDP offer broadcasts from servers.
        Also actively sends discovery requests to find servers.
        
        Returns:
            tuple: (server_ip, tcp_port, server_name) or None if timeout
        """
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # SO_REUSEPORT is not available on Windows, only use it on Linux/Mac
        try:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass  # Not available on Windows
        
        # Enable broadcast receiving and sending
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            # Bind to all interfaces on the broadcast port
            udp_socket.bind(('0.0.0.0', UDP_BROADCAST_PORT))
            udp_socket.settimeout(1.0)  # Short timeout for active scanning
            
            print("Client started, listening for offer requests...")
            
            max_attempts = 60  # Try for about 60 seconds
            attempts = 0
            
            while attempts < max_attempts:
                try:
                    data, server_addr = udp_socket.recvfrom(1024)
                    
                    # Validate minimum size
                    if len(data) < 39:
                        continue
                    
                    offer = unpack_offer(data)
                    if offer is None:
                        continue  # Invalid offer (wrong magic cookie or type), keep listening
                    
                    tcp_port, server_name = offer
                    server_ip = server_addr[0]
                    
                    print(f"Received offer from {server_ip} (Server: {server_name})")
                    return (server_ip, tcp_port, server_name)
                    
                except socket.timeout:
                    attempts += 1
                    continue
                except Exception as e:
                    # Ignore any malformed packets
                    continue
                    
        except OSError as e:
            print(f"[!] Error binding to port {UDP_BROADCAST_PORT}: {e}")
            print("[!] Port might be in use. Try closing other clients or wait a moment.")
            return None
        except Exception as e:
            print(f"[!] Error listening for offers: {e}")
            return None
        finally:
            udp_socket.close()
        
        return None
    
    def receive_card(self, tcp_socket):
        """
        Receive a card from the server.
        
        Args:
            tcp_socket: TCP socket connected to the server
        
        Returns:
            tuple: (result, rank, suit) or None if error
        """
        try:
            # No timeout - wait for server as long as needed
            data = tcp_socket.recv(SERVER_PAYLOAD_SIZE)
            if not data:
                print("[!] Server disconnected")
                return None
            
            if len(data) < SERVER_PAYLOAD_SIZE:
                print(f"[!] Incomplete data received: {len(data)} bytes")
                return None
            
            payload = unpack_server_payload(data)
            if payload is None:
                print("[!] Invalid payload from server")
                return None
            
            return payload
            
        except ConnectionResetError:
            print("[!] Connection reset by server")
            return None
        except Exception as e:
            print(f"[!] Error receiving card: {e}")
            return None
    
    def send_action(self, tcp_socket, action):
        """
        Send a player action (hit or stand) to the server.
        
        Args:
            tcp_socket: TCP socket connected to the server
            action: "hit" or "stand"
        """
        payload = pack_client_payload(action)
        tcp_socket.send(payload)
    
    def get_player_decision(self, player_sum, player_cards):
        """
        Get the player's decision (hit or stand).
        This is where you can implement your strategy!
        
        Args:
            player_sum: Current sum of player's cards
            player_cards: List of player's cards
        
        Returns:
            str: "hit" or "stand"
        """
        from constants import GREEN, CYAN, YELLOW, RESET
        
        print(f"\n  {YELLOW}Your current sum: {player_sum}{RESET}")
        print(f"  [{GREEN}H{RESET}]it or [{CYAN}S{RESET}]tand? ", end="")
        
        while True:
            try:
                choice = input().strip().lower()
                if choice in ['h', 'hit']:
                    return "hit"
                elif choice in ['s', 'stand']:
                    return "stand"
                else:
                    print("  Invalid choice. Enter 'h' or 's': ", end="")
            except EOFError:
                # In case of automated testing, use simple strategy
                return "stand" if player_sum >= 17 else "hit"
    
    def play_round(self, tcp_socket, round_num):
        """
        Play a single round of Blackjack.
        
        Args:
            tcp_socket: TCP socket connected to the server
            round_num: Current round number
        
        Returns:
            str: "win", "loss", "tie" or None if error
        """
        from constants import GREEN, YELLOW, CYAN, RED, RESET, BOLD, make_box, pad_line
        
        # Simple round header
        header = f"{CYAN}┌{'─' * 38}┐{RESET}"
        title = f"ROUND {round_num}".center(38)
        title_line = f"{CYAN}│{RESET}{YELLOW}{BOLD}{title}{RESET}{CYAN}│{RESET}"
        footer = f"{CYAN}└{'─' * 38}┘{RESET}"
        print(f"\n{header}\n{title_line}\n{footer}")
        
        player_cards = []
        dealer_visible_cards = []
        
        # Receive initial 2 player cards
        for i in range(2):
            payload = self.receive_card(tcp_socket)
            if payload is None:
                return None
            result, rank, suit = payload
            player_cards.append((rank, suit))
            print(f"  You received: {card_to_string(rank, suit)}")
        
        # Receive dealer's visible card
        payload = self.receive_card(tcp_socket)
        if payload is None:
            return None
        result, rank, suit = payload
        dealer_visible_cards.append((rank, suit))
        print(f"\n  Dealer shows: {card_to_string(rank, suit)}")
        
        # Calculate initial sum
        player_sum = sum(get_card_value(r) for r, s in player_cards)
        print(f"  Your sum: {YELLOW}{player_sum}{RESET}")
        
        # Player's turn
        while player_sum < 21:
            action = self.get_player_decision(player_sum, player_cards)
            self.send_action(tcp_socket, action)
            
            if action == "stand":
                print(f"  You chose to {CYAN}STAND{RESET}")
                # Receive acknowledgment
                payload = self.receive_card(tcp_socket)
                break
            else:
                print(f"  You chose to {GREEN}HIT{RESET}")
                
                # Receive new card
                payload = self.receive_card(tcp_socket)
                if payload is None:
                    return None
                
                result, rank, suit = payload
                
                if rank > 0:  # Valid card
                    player_cards.append((rank, suit))
                    player_sum = sum(get_card_value(r) for r, s in player_cards)
                    print(f"  You received: {card_to_string(rank, suit)}")
                    print(f"  Your sum: {YELLOW}{player_sum}{RESET}")
                
                # Check for bust or game end
                if result == RESULT_LOSS:
                    print(f"\n  {RED}BUSTED!{RESET}")
                    return "loss"
                elif result == RESULT_WIN:
                    print(f"\n  {GREEN}YOU WIN!{RESET}")
                    return "win"
                elif result == RESULT_TIE:
                    print(f"\n  {YELLOW}TIE!{RESET}")
                    return "tie"
        
        # If we get here, player stood or hit 21 - now it's dealer's turn
        print(f"\n  {CYAN}--- Dealer's Turn ---{RESET}")
        
        # Receive dealer's hidden card
        payload = self.receive_card(tcp_socket)
        if payload is None:
            return None
        result, rank, suit = payload
        if rank > 0:
            dealer_visible_cards.append((rank, suit))
            print(f"  Dealer reveals: {card_to_string(rank, suit)}")
        
        dealer_sum = sum(get_card_value(r) for r, s in dealer_visible_cards)
        print(f"  Dealer's sum: {YELLOW}{dealer_sum}{RESET}")
        
        # Receive dealer's additional cards until result is final
        while result == RESULT_ROUND_NOT_OVER:
            payload = self.receive_card(tcp_socket)
            if payload is None:
                return None
            
            result, rank, suit = payload
            
            if rank > 0:  # Valid card
                dealer_visible_cards.append((rank, suit))
                dealer_sum = sum(get_card_value(r) for r, s in dealer_visible_cards)
                print(f"  Dealer draws: {card_to_string(rank, suit)}")
                print(f"  Dealer's sum: {YELLOW}{dealer_sum}{RESET}")
        
        # Final result
        if result == RESULT_WIN:
            print(f"\n  {GREEN}YOU WIN! (You: {player_sum} vs Dealer: {dealer_sum}){RESET}")
            return "win"
        elif result == RESULT_LOSS:
            print(f"\n  {RED}YOU LOSE! (You: {player_sum} vs Dealer: {dealer_sum}){RESET}")
            return "loss"
        else:
            print(f"\n  {YELLOW}TIE! (Both have {player_sum}){RESET}")
            return "tie"
    
    def play_game(self, server_ip, tcp_port, server_name, num_rounds):
        """
        Connect to a server and play the requested number of rounds.
        
        Args:
            server_ip: IP address of the server
            tcp_port: TCP port to connect to
            server_name: Name of the server
            num_rounds: Number of rounds to play
        
        Returns:
            bool: True if game completed successfully
        """
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            # Connect with a timeout, then remove it for game play
            tcp_socket.settimeout(10.0)  # 10 seconds to connect
            tcp_socket.connect((server_ip, tcp_port))
            tcp_socket.settimeout(None)  # No timeout during game - wait as long as needed
            
            print(f"\n[+] Connected to {server_name} at {server_ip}:{tcp_port}")
            
            # Send request
            request = pack_request(num_rounds, self.team_name)
            tcp_socket.send(request)
            
            print(f"[*] Playing {num_rounds} rounds against {server_name}")
            
            # Play rounds
            wins = 0
            losses = 0
            ties = 0
            
            for round_num in range(1, num_rounds + 1):
                result = self.play_round(tcp_socket, round_num)
                
                if result is None:
                    print("[!] Game ended unexpectedly")
                    return False
                
                if result == "win":
                    wins += 1
                    self.total_wins += 1
                elif result == "loss":
                    losses += 1
                    self.total_losses += 1
                else:
                    ties += 1
                    self.total_ties += 1
            
            # Print final statistics
            total = wins + losses + ties
            win_rate = (wins / total * 100) if total > 0 else 0
            
            from constants import GREEN, YELLOW, CYAN, RED, RESET, BOLD, make_box
            
            lines = [
                f"Rounds played: {num_rounds}",
                f"{GREEN}Wins: {wins}{RESET}  {RED}Losses: {losses}{RESET}  {CYAN}Ties: {ties}{RESET}",
                f"Win Rate: {YELLOW}{win_rate:.1f}%{RESET}"
            ]
            box = make_box("GAME COMPLETE!", lines, width=40, border_color=GREEN)
            print(f"\n{box}\n")
            
            return True
            
        except socket.timeout:
            print(f"[!] Connection to {server_name} timed out")
            return False
        except ConnectionRefusedError:
            print(f"[!] Connection to {server_name} refused")
            return False
        except Exception as e:
            print(f"[!] Error during game: {e}")
            return False
        finally:
            tcp_socket.close()
    
    def get_menu_choice(self):
        """
        Show menu and get user's choice.
        
        Returns:
            tuple: (choice, num_rounds) where choice is 'play' or 'quit'
        """
        from constants import GREEN, YELLOW, CYAN, RED, RESET, BOLD
        
        print(f"\n{CYAN}{'─' * 40}{RESET}")
        print(f"  {YELLOW}[P]{RESET} Play again")
        print(f"  {YELLOW}[Q]{RESET} Quit")
        print(f"{CYAN}{'─' * 40}{RESET}")
        
        while True:
            try:
                choice = input(f"  Choose: ").strip().lower()
                
                if choice in ['q', 'quit', 'exit']:
                    return ('quit', 0)
                elif choice in ['p', 'play', '']:
                    # Ask for number of rounds
                    while True:
                        try:
                            rounds_input = input(f"  How many rounds? [1-255]: ").strip()
                            if rounds_input == '':
                                num_rounds = 3  # Default
                            else:
                                num_rounds = int(rounds_input)
                            
                            if 1 <= num_rounds <= 255:
                                return ('play', num_rounds)
                            else:
                                print("  Please enter a number between 1 and 255")
                        except ValueError:
                            print("  Please enter a valid number")
                else:
                    print(f"  Invalid choice. Enter {YELLOW}P{RESET} to play or {YELLOW}Q{RESET} to quit")
            except EOFError:
                return ('quit', 0)
    
    def run(self):
        """
        Main client loop - repeatedly listen for offers and play games.
        """
        from constants import GREEN, YELLOW, CYAN, RED, RESET, BOLD, make_box
        
        box = make_box(
            "♠ ♥ ♣ ♦  B L A C K J A C K  ♦ ♣ ♥ ♠",
            [f"{CYAN}Team: {self.team_name}{RESET}"],
            width=44,
            title_color=YELLOW,
            border_color=GREEN
        )
        print(f"\n{box}\n")
        
        # Get initial number of rounds
        while True:
            try:
                print(f"  How many rounds would you like to play? ", end="")
                num_rounds = int(input())
                if 1 <= num_rounds <= 255:
                    break
                else:
                    print("  Please enter a number between 1 and 255")
            except ValueError:
                print("  Please enter a valid number")
            except EOFError:
                num_rounds = 3
                break
        
        self.running = True
        
        while self.running:
            try:
                # Listen for server offers
                offer = self.listen_for_offers()
                
                if offer is None:
                    print("[!] No server found, retrying...")
                    continue
                
                server_ip, tcp_port, server_name = offer
                
                # Play the game
                self.play_game(server_ip, tcp_port, server_name, num_rounds)
                
                # Show menu after game
                choice, new_rounds = self.get_menu_choice()
                
                if choice == 'quit':
                    break
                else:
                    num_rounds = new_rounds
                    print("\n[*] Looking for next game...")
                
            except KeyboardInterrupt:
                print("\n[!] Client shutting down...")
                break
            except Exception as e:
                print(f"[!] Error: {e}, retrying...")
                continue
        
        print(f"\n{YELLOW}Thanks for playing! Goodbye!{RESET}\n")


def main():
    """
    Main entry point for the client.
    """
    client = BlackjackClient(TEAM_NAME)
    client.run()


if __name__ == "__main__":
    main()
