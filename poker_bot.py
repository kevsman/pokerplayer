from bs4 import BeautifulSoup
import re
import sys
from hand_evaluator import HandEvaluator
from html_parser import PokerPageParser
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE # Updated import
from ui_controller import UIController # Added import
import time

# Action definitions

class PokerBot:
    def __init__(self, html_content=None, big_blind=0.02, small_blind=0.01):
        self.parser = PokerPageParser(html_content) if html_content else None
        self.hand_evaluator = HandEvaluator()
        self.decision_engine = DecisionEngine(big_blind, small_blind)
        self.ui_controller = UIController() # Added UIController instance
        self.table_data = {}
        self.player_data = []
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.running = False
        self.last_html_content = None

    def analyze_table(self):
        self.table_data = self.parser.analyze_table()

    def analyze_players(self):
        self.player_data = self.parser.analyze_players()
        
        for player_info in self.player_data:
            if player_info.get('is_my_player') and player_info.get('cards'):
                community_cards = self.table_data.get('community_cards', [])
                # Store the full evaluation tuple from HandEvaluator
                player_info['hand_evaluation'] = self.hand_evaluator.calculate_best_hand(player_info['cards'], community_cards)
                # Keep the string description for summary purposes if needed
                player_info['hand_rank'] = player_info['hand_evaluation'][1] 
            elif not player_info.get('is_my_player') and player_info.get('has_hidden_cards'):
                player_info['hand_rank'] = "N/A (Hidden Cards)"
                player_info['hand_evaluation'] = (0, "N/A (Hidden Cards)", []) # Default eval for others
            else:
                player_info['hand_rank'] = "N/A"
                player_info['hand_evaluation'] = (0, "N/A", []) # Default eval for empty/no cards


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
    
    def get_suggested_action(self):
        if not self.table_data or not self.player_data:
            self.analyze() # Ensure data is up-to-date

        my_player = self.get_my_player()

        if not my_player:
            return "Could not find my player data."
        
        # The DecisionEngine's make_decision expects: my_player, table_data, all_players_data
        # It also internally checks if it's the player's turn.
        return self.decision_engine.make_decision(my_player, self.table_data, self.player_data)

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
                # hand_rank_str is already set from hand_evaluation[1] above
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

    def get_game_state_from_html(self, html_content):
        self.parser = PokerPageParser(html_content)
        self.analyze()

    def run_calibration(self):
        print("Starting UI calibration...")
        self.ui_controller.calibrate_all()
        print("Calibration finished. Positions saved in config.json")

    def main_loop(self):
        self.running = True
        print("PokerBot started. Press Ctrl+C to stop.")
        
        if not self.ui_controller.positions:
            print("UI positions not calibrated. Please run calibration first or ensure config.json exists.")
            choice = input("Would you like to run calibration now? (yes/no): ").strip().lower()
            if choice == 'yes':
                self.run_calibration()
            else:
                print("Exiting. Please calibrate UI positions before running the bot.")
                return

        try:
            while self.running:
                print("\n--- New Decision Cycle ---")
                print("Attempting to retrieve game HTML from screen...")
                current_html = self.ui_controller.get_html_from_screen()

                if not current_html:
                    print("Failed to retrieve HTML. Retrying in 1 second...")
                    time.sleep(1) # Changed from 5 seconds
                    continue
                
                # Removed the check: if current_html == self.last_html_content:
                # HTML will be processed every cycle now.
                self.last_html_content = current_html

                # 2. Parse HTML to get game state
                # Assuming self.parser.parse_html(current_html) returns a dict 
                # like game_state = {'my_player_data': ..., 'table_data': ..., 'all_players_data': ...}
                # or None/throws error on failure.
                game_state = self.parser.parse_html(current_html)
                if not game_state:
                    print("Failed to parse HTML or critical data missing. Retrying in 1 second...")
                    time.sleep(1)
                    continue

                my_player_data = game_state.get('my_player_data')
                table_data = game_state.get('table_data')
                all_players_data = game_state.get('all_players_data')

                if not my_player_data or not table_data or not all_players_data:
                    print("Essential game data missing after parsing. Retrying in 1 second...")
                    time.sleep(1)
                    continue

                if my_player_data and my_player_data.get('has_turn'):
                    print(f"My turn. Hand: {my_player_data.get('cards')}, Stack: {my_player_data.get('stack')}")
                    print(f"Pot: {table_data.get('pot_size')}, Community Cards: {table_data.get('community_cards')}")

                    action_tuple = self.decision_engine.make_decision(my_player_data, table_data, all_players_data)
                    
                    action = ""
                    amount = None
                    if isinstance(action_tuple, tuple) and len(action_tuple) == 2:
                        action, amount = action_tuple
                    elif isinstance(action_tuple, str):
                        action = action_tuple
                    else:
                        print(f"Warning: Unknown action format from decision engine: {action_tuple}")
                        action = ACTION_FOLD

                    print(f"Decision: {action}" + (f" Amount: {amount}" if amount is not None else ""))

                    if action == ACTION_FOLD:
                        self.ui_controller.action_fold()
                    elif action == ACTION_CHECK or action == ACTION_CALL:
                        self.ui_controller.action_check_call()
                    elif action == ACTION_RAISE:
                        self.ui_controller.action_raise(amount=amount)
                    else:
                        print(f"Unknown action: {action}")
                    
                    time.sleep(2) # Wait a bit after an action for game state to update on screen
                else:
                    if my_player_data: # Successfully parsed, but not our turn
                         print(f"Not my turn. My Hand: {my_player_data.get('cards')}. Waiting...")
                    else: # Should not happen if parsing check above is robust
                         print("Player data not found or not my turn. Waiting...")
                
                time.sleep(1) # Main loop delay to aim for ~1 second cycle + processing time

        except KeyboardInterrupt:
            print("PokerBot stopped by user.")
        finally:
            self.running = False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            print(f"Attempting to open and parse: {file_path}")
            bot = PokerBot(html_content) # Default blinds will be used
            analysis_result = bot.analyze()
            
            print("\n---- Summary from PokerBot ----")
            print(bot.get_summary())

            my_player_info = bot.get_my_player()
            # Check for turn is now handled within get_suggested_action or make_decision
            # but we can still check here to provide a clearer message if it's not our turn before calling.
            if my_player_info and my_player_info.get('has_turn'):
                decision = bot.get_suggested_action() # Changed from make_decision
                if isinstance(decision, tuple):
                    # Ensure amount is formatted nicely if it's a float
                    action_amount = decision[1]
                    if isinstance(action_amount, float):
                        action_amount_str = f"{action_amount:.2f}"
                    else:
                        action_amount_str = str(action_amount)
                    print(f"\n---- Suggested Action ----: {decision[0]} {action_amount_str}")
                else:
                    print(f"\n---- Suggested Action ----: {decision}")
            elif my_player_info:
                print("\nNot my turn to act.")
            else:
                print("\nCould not find my player information.")
            

            # For detailed debugging, uncomment the following lines:
            # print("\n---- Raw Analysis Result (for debugging) ----")
            # import json
            # print(json.dumps(analysis_result, indent=2))

        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        bot = PokerBot()
        # bot.run_calibration() # Uncomment this line and run `python poker_bot.py` once to calibrate
        bot.main_loop()

