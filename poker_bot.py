from bs4 import BeautifulSoup
import re
import sys
from hand_evaluator import HandEvaluator
from html_parser import PokerPageParser

class PokerBot:
    def __init__(self, html_content):
        self.parser = PokerPageParser(html_content)
        self.hand_evaluator = HandEvaluator()
        self.table_data = {}
        self.player_data = []

    def analyze_table(self):
        self.table_data = self.parser.analyze_table()

    def analyze_players(self):
        self.player_data = self.parser.analyze_players()
        
        for player_info in self.player_data:
            if player_info.get('is_my_player') and player_info.get('cards'):
                community_cards = self.table_data.get('community_cards', [])
                player_info['hand_rank'] = self.hand_evaluator.calculate_best_hand(player_info['cards'], community_cards)
            elif not player_info.get('is_my_player') and player_info.get('has_hidden_cards'):
                player_info['hand_rank'] = "N/A (Hidden Cards)"
            else:
                player_info['hand_rank'] = "N/A"


    def get_active_player(self):
        for player in self.player_data:
            if player.get('has_turn', False):
                return player
        return None
        
    def get_my_player(self):
        for player in self.player_data:
            if player.get('is_my_player', False):
                return player
        return None

    def analyze(self):
        self.analyze_table() 
        self.analyze_players() 
        return {
            'table': self.table_data,
            'players': self.player_data,
            'my_player': self.get_my_player(),
            'active_player': self.get_active_player()
        }
    
    def get_summary(self):
        if not self.table_data and not self.player_data: 
            self.analyze()
            
        summary = []
        summary.append(f"--- Table --- Hand ID: {self.table_data.get('hand_id', 'N/A')}")
        summary.append(f"Pot: {self.table_data.get('pot_size', 'N/A')}")
        summary.append(f"Game Stage: {self.table_data.get('game_stage', 'N/A')}")
        
        cc_list = self.table_data.get('community_cards', [])
        cc_text = ' '.join(cc_list) if cc_list else "None"
        summary.append(f"Community Cards: {cc_text}")
        summary.append(f"Dealer Position: Seat {self.table_data.get('dealer_position', 'N/A')}")
        
        summary.append("\n--- Players ---")
        if not self.player_data:
            summary.append("  No player data found or analyzed.")
        
        sorted_players = sorted(
            [p for p in self.player_data if p.get('seat') is not None], 
            key=lambda p: int(p['seat']) if p['seat'].isdigit() else 999
        )

        for player in sorted_players:
            if player.get('is_empty', False):
                summary.append(f"  Seat {player.get('seat', 'N/A')}: Empty")
                continue
                
            name = player.get('name', 'N/A')
            stack = player.get('stack', 'N/A')
            bet = player.get('bet', '0') 
            
            status = []
            if player.get('is_my_player', False):
                status.append("ME")
                hand_rank_str = player.get('hand_rank', 'N/A') 
                if hand_rank_str and hand_rank_str != 'N/A':
                    status.append(f"Hand: {hand_rank_str}")

            if player.get('has_turn', False): status.append("ACTIVE TURN")
            status_text = f" ({', '.join(status)})" if status else ""
            
            cards_text = ""
            if player.get('cards') and player['cards']:
                cards_text = f" Cards: {' '.join(player.get('cards'))}"
            elif player.get('has_hidden_cards', False):
                cards_text = " (Has hidden cards)"
                
            summary.append(f"  Seat {player.get('seat', 'N/A')}: {name}{status_text} - Stack: {stack}, Bet: {bet}{cards_text}")
        
        active_player = self.get_active_player()
        if active_player:
            summary.append(f"\nIt is currently Seat {active_player['seat']} ({active_player['name']})'s turn.")
        else:
            summary.append("\nNo player currently has the turn (or turn detection failed).")
            
        my_player = self.get_my_player()
        if my_player and my_player.get('has_turn'):
            summary.append("It is YOUR turn to act.")

        return "\n".join(summary)

    # Hand ranking logic has been moved to hand_evaluator.py

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            print(f"Attempting to open and parse: {file_path}")
            bot = PokerBot(html_content)
            analysis_result = bot.analyze()
            
            print("\n---- Summary from PokerBot ----")
            print(bot.get_summary())

            # For detailed debugging, uncomment the following lines:
            # print("\n---- Raw Analysis Result (for debugging) ----")
            # import json
            # print(json.dumps(analysis_result, indent=2))

        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print("Usage: python poker_bot.py <path_to_html_file>")

