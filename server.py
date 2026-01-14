"""
Blackjack Server - Hosts the game and handles client connections.

The server:
1. Broadcasts UDP offer messages every second
2. Accepts TCP connections from clients
3. Manages the Blackjack game logic
"""

import socket
import struct
import threading
import random
import time
from constants import (
    UDP_BROADCAST_PORT, OFFER_INTERVAL, TCP_TIMEOUT,
    RESULT_WIN, RESULT_LOSS, RESULT_TIE, RESULT_ROUND_NOT_OVER,
    TEAM_NAME, get_card_value, SUITS, RANK_NAMES
)
from protocol import (
    pack_offer, unpack_request, pack_server_payload,
    unpack_client_payload, card_to_string
)


class Deck:
    """
    Represents a standard 52-card deck.
    """
    
    def __init__(self):
        """Initialize and shuffle a new deck."""
        self.reset()
    
    def reset(self):
        """Reset and shuffle the deck."""
        # Create all 52 cards: (rank, suit) where rank is 1-13, suit is 0-3
        self.cards = [(rank, suit) for rank in range(1, 14) for suit in range(4)]
        random.shuffle(self.cards)
    
    def draw(self):
        """
        Draw a card from the deck.
        
        Returns:
            tuple: (rank, suit) of the drawn card
        """
        if len(self.cards) == 0:
            self.reset()
        return self.cards.pop()


class BlackjackGame:
    """
    Handles a single Blackjack game session with a client.
    """
    
    def __init__(self, client_socket, client_address, client_name, num_rounds):
        """
        Initialize a new game session.
        
        Args:
            client_socket: TCP socket connected to the client
            client_address: Address of the client
            client_name: Name of the client team
            num_rounds: Number of rounds to play
        """
        self.client_socket = client_socket
        self.client_address = client_address
        self.client_name = client_name
        self.num_rounds = num_rounds
        self.deck = Deck()
        
        # Game state
        self.player_cards = []
        self.dealer_cards = []
        self.player_sum = 0
        self.dealer_sum = 0
    
    def calculate_sum(self, cards):
        """
        Calculate the sum of card values.
        
        Args:
            cards: List of (rank, suit) tuples
        
        Returns:
            int: Total value of the cards
        """
        return sum(get_card_value(rank) for rank, suit in cards)
    
    def send_card(self, card, result=RESULT_ROUND_NOT_OVER):
        """
        Send a card to the client.
        
        Args:
            card: (rank, suit) tuple
            result: Game result code
        """
        rank, suit = card
        payload = pack_server_payload(result, rank, suit)
        self.client_socket.send(payload)
    
    def receive_action(self):
        """
        Receive the player's action (hit or stand).
        
        Returns:
            str: "hit" or "stand" or None if error
        """
        try:
            # No timeout - wait for player as long as needed
            data = self.client_socket.recv(1024)
            if not data:
                return None
            return unpack_client_payload(data)
        except ConnectionResetError:
            print(f"  [!] {self.client_name} disconnected")
            return None
        except Exception as e:
            print(f"  [!] Error receiving action: {e}")
            return None
    
    def play_round(self, round_num):
        """
        Play a single round of Blackjack.
        
        Args:
            round_num: Current round number
        
        Returns:
            str: "win", "loss", or "tie"
        """
        print(f"\n  === Round {round_num} vs {self.client_name} ===")
        
        # Reset for new round
        self.deck.reset()
        self.player_cards = []
        self.dealer_cards = []
        
        # Deal initial cards
        # Player gets 2 cards (both visible)
        card1 = self.deck.draw()
        card2 = self.deck.draw()
        self.player_cards = [card1, card2]
        self.player_sum = self.calculate_sum(self.player_cards)
        
        # Dealer gets 2 cards (first visible, second hidden)
        dealer_card1 = self.deck.draw()
        dealer_card2 = self.deck.draw()  # Hidden card
        self.dealer_cards = [dealer_card1, dealer_card2]
        
        print(f"  Player's cards: {card_to_string(*card1)}, {card_to_string(*card2)} (sum: {self.player_sum})")
        print(f"  Dealer's visible card: {card_to_string(*dealer_card1)}")
        
        # Send initial cards to player
        self.send_card(card1)
        self.send_card(card2)
        # Send dealer's visible card
        self.send_card(dealer_card1)
        
        # Player's turn
        while self.player_sum < 21:
            action = self.receive_action()
            
            if action is None:
                print(f"  [!] Invalid action from {self.client_name}, ending game")
                return None
            
            print(f"  Player chose: {action}")
            
            if action == "stand":
                # Send acknowledgment with no new card
                self.send_card((0, 'H'), RESULT_ROUND_NOT_OVER)
                break
            elif action == "hit":
                new_card = self.deck.draw()
                self.player_cards.append(new_card)
                self.player_sum = self.calculate_sum(self.player_cards)
                
                print(f"  Player drew: {card_to_string(*new_card)} (new sum: {self.player_sum})")
                
                # Check if player busted
                if self.player_sum > 21:
                    print(f"  Player BUSTED!")
                    self.send_card(new_card, RESULT_LOSS)
                    return "loss"
                else:
                    self.send_card(new_card, RESULT_ROUND_NOT_OVER)
        
        # Player didn't bust - dealer's turn
        print(f"\n  Dealer reveals hidden card: {card_to_string(*dealer_card2)}")
        self.dealer_sum = self.calculate_sum(self.dealer_cards)
        print(f"  Dealer's initial sum: {self.dealer_sum}")
        
        # Send dealer's hidden card
        self.send_card(dealer_card2)
        
        # Dealer draws until sum >= 17
        while self.dealer_sum < 17:
            new_card = self.deck.draw()
            self.dealer_cards.append(new_card)
            self.dealer_sum = self.calculate_sum(self.dealer_cards)
            
            print(f"  Dealer drew: {card_to_string(*new_card)} (new sum: {self.dealer_sum})")
            self.send_card(new_card)
        
        # Determine winner
        if self.dealer_sum > 21:
            print(f"  Dealer BUSTED! Player wins!")
            result = "win"
            result_code = RESULT_WIN
        elif self.player_sum > self.dealer_sum:
            print(f"  Player wins! ({self.player_sum} vs {self.dealer_sum})")
            result = "win"
            result_code = RESULT_WIN
        elif self.dealer_sum > self.player_sum:
            print(f"  Dealer wins! ({self.dealer_sum} vs {self.player_sum})")
            result = "loss"
            result_code = RESULT_LOSS
        else:
            print(f"  Tie! ({self.player_sum} vs {self.dealer_sum})")
            result = "tie"
            result_code = RESULT_TIE
        
        # Send final result (with dummy card)
        self.send_card((0, 'H'), result_code)
        
        return result
    
    def run(self):
        """
        Run the complete game session.
        """
        print(f"\n[*] Starting game with {self.client_name} for {self.num_rounds} rounds")
        
        wins = 0
        losses = 0
        ties = 0
        
        for round_num in range(1, self.num_rounds + 1):
            result = self.play_round(round_num)
            
            if result is None:
                print(f"[!] Game ended unexpectedly")
                break
            
            if result == "win":
                losses += 1  # Player won = dealer loss
            elif result == "loss":
                wins += 1  # Player lost = dealer win
            else:
                ties += 1
        
        print(f"\n[*] Game with {self.client_name} completed!")
        print(f"    Dealer stats - Wins: {wins}, Losses: {losses}, Ties: {ties}")


class BlackjackServer:
    """
    Main server class that handles UDP broadcasts and TCP connections.
    """
    
    def __init__(self, team_name=TEAM_NAME):
        """
        Initialize the server.
        
        Args:
            team_name: Name of the server team
        """
        self.team_name = team_name
        self.running = False
        
        # Create TCP socket
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass  # SO_REUSEPORT not available on this platform
        self.tcp_socket.bind(('', 0))  # Bind to any available port
        self.tcp_port = self.tcp_socket.getsockname()[1]
        
        # Create UDP socket for broadcasts
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    def get_local_ip(self):
        """
        Get the local IP address of this machine.
        
        Returns:
            str: Local IP address
        """
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def get_broadcast_addresses(self):
        """
        Get list of broadcast addresses to send to.
        
        Returns:
            list: List of broadcast addresses
        """
        addresses = ['<broadcast>', '255.255.255.255']
        
        # Calculate subnet broadcast address from local IP
        local_ip = self.get_local_ip()
        if local_ip != "127.0.0.1":
            # Assume /24 subnet (255.255.255.0) - most common
            parts = local_ip.split('.')
            if len(parts) == 4:
                subnet_broadcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                addresses.append(subnet_broadcast)
                
                # For hotspots that block broadcast, also send to common IP ranges
                # Most hotspots use .1-.20 range for clients
                for i in range(1, 30):
                    addresses.append(f"{parts[0]}.{parts[1]}.{parts[2]}.{i}")
        
        return addresses
    
    def broadcast_offers(self):
        """
        Continuously broadcast UDP offer messages.
        Runs in a separate thread.
        """
        offer_message = pack_offer(self.tcp_port, self.team_name)
        broadcast_addresses = self.get_broadcast_addresses()
        
        print(f"[*] Broadcasting to: {broadcast_addresses}")
        
        while self.running:
            try:
                # Broadcast to multiple addresses for better compatibility
                for addr in broadcast_addresses:
                    try:
                        self.udp_socket.sendto(offer_message, (addr, UDP_BROADCAST_PORT))
                    except:
                        pass
            except Exception as e:
                print(f"[!] Error broadcasting offer: {e}")
            
            time.sleep(OFFER_INTERVAL)
    
    def handle_client(self, client_socket, client_address):
        """
        Handle a single client connection.
        
        Args:
            client_socket: TCP socket connected to the client
            client_address: Address of the client
        """
        print(f"\n[+] New connection from {client_address}")
        
        try:
            # No global timeout - connection stays open until game ends
            # Individual operations will set their own timeouts as needed
            
            # Receive request message (with timeout for initial request)
            client_socket.settimeout(30.0)  # 30 seconds to send request
            data = client_socket.recv(1024)
            if not data:
                print(f"[-] Empty request from {client_address}")
                return
            
            request = unpack_request(data)
            if request is None:
                print(f"[-] Invalid request from {client_address}")
                return
            
            num_rounds, client_name = request
            print(f"[+] {client_name} wants to play {num_rounds} rounds")
            
            # Start the game
            game = BlackjackGame(client_socket, client_address, client_name, num_rounds)
            game.run()
            
        except socket.timeout:
            print(f"[-] Timeout with client {client_address}")
        except Exception as e:
            print(f"[-] Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            print(f"[-] Connection closed with {client_address}")
    
    def start(self):
        """
        Start the server - begin broadcasting and accepting connections.
        """
        self.running = True
        local_ip = self.get_local_ip()
        
        print("=" * 50)
        print(f"  Blackjack Server - {self.team_name}")
        print("=" * 50)
        print(f"Server started, listening on IP address {local_ip}")
        print(f"TCP Port: {self.tcp_port}")
        print(f"Broadcasting offers on UDP port {UDP_BROADCAST_PORT}")
        print("=" * 50)
        
        # Start broadcast thread
        broadcast_thread = threading.Thread(target=self.broadcast_offers, daemon=True)
        broadcast_thread.start()
        
        # Start listening for TCP connections
        self.tcp_socket.listen(5)
        
        try:
            while self.running:
                try:
                    client_socket, client_address = self.tcp_socket.accept()
                    
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                    
        except KeyboardInterrupt:
            print("\n[!] Server shutting down...")
        finally:
            self.stop()
    
    def stop(self):
        """
        Stop the server.
        """
        self.running = False
        self.tcp_socket.close()
        self.udp_socket.close()
        print("[*] Server stopped")


def main():
    """
    Main entry point for the server.
    """
    # You can change the team name here or pass it as argument
    server = BlackjackServer(TEAM_NAME)
    server.start()


if __name__ == "__main__":
    main()
