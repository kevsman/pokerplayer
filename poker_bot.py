from bs4 import BeautifulSoup
import re
import sys
from hand_evaluator import HandEvaluator
from html_parser import PokerPageParser
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE # Updated import
from ui_controller import UIController # Added import
import time
import logging # Added import

# Action definitions

def parse_currency_string(value_str):
    if isinstance(value_str, (int, float)):
        return float(value_str)
    if not isinstance(value_str, str):
        return 0.0 # Or raise an error, depending on desired handling
    cleaned_str = value_str.replace('€', '').replace('$', '').replace(',', '').strip()
    try:
        return float(cleaned_str)
    except ValueError:
        return 0.0 # Or raise an error

class PokerBot:
    # html_content parameter removed from __init__ signature
    def __init__(self, big_blind=0.02, small_blind=0.01):
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG) # Set to DEBUG to capture all levels of messages
        self.fh = None # Initialize fh to None
        self.ch = None # Initialize ch to None
        # Create file handler
        # Store file handler to close it later
        self.fh = logging.FileHandler('poker_bot.log', mode='a', encoding='utf-8') # Append mode, UTF-8 encoding
        self.fh.setLevel(logging.DEBUG)
        # Create console handler with a higher log level (optional, for cleaner console output)
        self.ch = logging.StreamHandler(sys.stdout) # Explicitly use sys.stdout
        self.ch.setLevel(logging.INFO)
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.fh.setFormatter(formatter)
        self.ch.setFormatter(formatter)
        # Add the handlers to the logger
        if not self.logger.handlers: # Avoid adding multiple handlers if __init__ is called multiple times
            self.logger.addHandler(self.fh)
            self.logger.addHandler(self.ch)

        try:
            self.parser = PokerPageParser() # Correctly instantiate with no arguments
            if self.parser is None: # This check is less likely to fail now
                self.logger.critical("self.parser is None after PokerPageParser() instantiation.")
                self.logger.critical("Please check the definition of the PokerPageParser class/function in html_parser.py.")
                self.logger.critical("It might be returning None or not be a class constructor.")
                raise RuntimeError("PokerPageParser could not be initialized properly.")
            
            if not hasattr(self.parser, 'parse_html'):
                error_msg = (
                    f"CRITICAL ERROR: self.parser (type: {type(self.parser)}) exists but does not have a 'parse_html' method. "
                    f"Please check the PokerPageParser class definition in html_parser.py."
                )
                self.logger.critical(error_msg)
                raise AttributeError(error_msg)

        except Exception as e:
            self.logger.critical(f"Failed to instantiate or validate PokerPageParser during PokerBot initialization: {e}")
            # Re-raise the exception to stop the bot if the parser is critical
            raise

        self.hand_evaluator = HandEvaluator()
        # self.decision_engine = DecisionEngine(big_blind, small_blind) # Old incorrect instantiation
        decision_engine_config = {'big_blind': big_blind, 'small_blind': small_blind}
        self.decision_engine = DecisionEngine(self.hand_evaluator, config=decision_engine_config)
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
            # In the context of file-based execution, analyze() might need to be called explicitly first
            # if parse_html was called on self.parser but analyze() on self (bot instance) wasn't.
            # However, analyze() itself calls self.parser.analyze_table/players which use the soup
            # set by the parser's parse_html method. So, if parser.parse_html was called, this should be fine.
            pass # analyze() will be called if needed by other methods or if data is empty
            
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

    # This method might need review based on its usage context.
    # The main_loop calls self.parser.parse_html directly.
    def get_game_state_from_html(self, html_content):
        if self.parser:
            self.parser.parse_html(html_content) # Use the parser instance's method
            self.analyze() # This will use the soup set in the parser by the call above
        # This method currently doesn't return a game_state dictionary.

    def run_calibration(self):
        self.logger.info("Starting UI calibration...")
        self.ui_controller.calibrate_all()
        self.logger.info("Calibration finished. Positions saved in config.json")

    def run_test_file(self, file_path):
        self.logger.info(f"--- Running Test with File: {file_path} ---")
        action = None
        amount = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_html = f.read()
            self.logger.info(f"HTML length: {len(current_html)}")
            if not current_html:
                self.logger.warning("Test HTML file is empty.")
                return ACTION_FOLD, 0

            parsed_state = self.parser.parse_html(current_html)
            if not parsed_state or parsed_state.get('error'):
                self.logger.error(f"Failed to parse HTML from test file: {parsed_state.get('error', 'Unknown parsing error') if parsed_state else 'Parser returned None'}")
                if parsed_state and parsed_state.get('warnings'):
                    for warning in parsed_state['warnings']:
                        self.logger.warning(f"Parser Warning: {warning}")
                return ACTION_FOLD, 0 
            
            if parsed_state.get('warnings'):
                for warning in parsed_state['warnings']:
                    self.logger.warning(f"Parser Warning: {warning}")

            self.analyze() 

            my_player_data = self.get_my_player()
            table_data = self.table_data
            all_players_data = self.player_data

            if not my_player_data or not table_data:
                self.logger.error("Essential game data missing after self.analyze() from test file.")
                return ACTION_FOLD, 0

            self.logger.info("\\\\n--- Game Summary from Test File ---")
            self.logger.info(self.get_summary())
            self.logger.info("--- End Game Summary ---")

            if my_player_data.get('has_turn'):
                hand_rank_description = my_player_data.get('hand_evaluation', (0, "N/A"))[1]
                self.logger.info(f"My turn. Hand: {my_player_data.get('cards')}, Rank: {hand_rank_description}, Stack: {my_player_data.get('stack')}")
                self.logger.info(f"Pot: {table_data.get('pot_size')}, Community Cards: {table_data.get('community_cards')}")
                
                if 'available_actions' in my_player_data:
                    self.logger.debug(f"Detected available actions: {my_player_data['available_actions']}")
                if my_player_data.get('is_all_in_call_available'):
                    self.logger.debug("Parser detected: All-in call is available.")

                action_tuple = self.decision_engine.make_decision(my_player_data, table_data, all_players_data)
                
                action = ""
                amount = 0 

                if isinstance(action_tuple, tuple) and len(action_tuple) == 2:
                    action, amount = action_tuple
                    if amount is None: 
                        amount = 0
                elif isinstance(action_tuple, str): 
                    action = action_tuple
                else:
                    self.logger.warning(f"Warning: Unknown action format from decision engine: {action_tuple}")
                    action = ACTION_FOLD
                    amount = 0 

                decision_log_message = f"Decision: {action}"
                if amount is not None:
                    decision_log_message += f" Amount: {amount:.2f}" 
                self.logger.info(decision_log_message)
                # Simulate UI actions (logging only for now)
                # ... (simulation logic as before) ...
                return action, amount
            else:
                if my_player_data:
                    self.logger.info(f"Not my turn. My Hand: {my_player_data.get('cards')}. Stack: {my_player_data.get('stack')}. Waiting...")
                else:
                    self.logger.info("Player data not found or not my turn. Waiting...")
                return ACTION_FOLD, 0 # Or some other appropriate default
        except Exception as e:
            self.logger.error(f"Error during test file run for {file_path}: {e}", exc_info=True)
            return ACTION_FOLD, 0 # Default to FOLD on error
        finally:
            self.logger.info(f"--- Test File Run Finished for: {file_path} ---")
            # self.close_logger() # Closing logger here might be too soon if bot instance is reused.
                               # Let's call it from the main script or test runner.

    def close_logger(self):
        """Closes the log handlers."""
        if self.fh:
            self.logger.removeHandler(self.fh)
            self.fh.close()
            self.fh = None
        if self.ch:
            self.logger.removeHandler(self.ch)
            self.ch.close()
            self.ch = None
        # Also remove any other handlers that might have been added, though less likely here
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

    def main_loop(self):
        self.running = True
        self.logger.info("PokerBot started. Press Ctrl+C to stop.")
        
        if not self.ui_controller.positions:
            self.logger.warning("UI positions not calibrated. Please run calibration first or ensure config.json exists.")
            choice = input("Would you like to run calibration now? (yes/no): ").strip().lower()
            if choice == 'yes':
                self.run_calibration()
            else:
                self.logger.info("Exiting. Please calibrate UI positions before running the bot.")
                return

        try:
            while self.running:
                self.logger.info("\n--- New Decision Cycle ---")
                self.logger.debug("Attempting to retrieve game HTML from screen...")
                current_html = self.ui_controller.get_html_from_screen()
                if current_html:
                    self.logger.debug(f"HTML length: {len(current_html)}") # Added print
                else:
                    self.logger.warning("HTML length: 0 (Failed to retrieve)") # Added print for failure case

                if not current_html:
                    self.logger.warning("Failed to retrieve HTML. Retrying in 1 second...")
                    time.sleep(1) # Changed from 5 seconds
                    continue
                
                # Removed the check: if current_html == self.last_html_content:
                # HTML will be processed every cycle now.
                self.last_html_content = current_html

                # 2. Parse HTML to get game state
                # Assuming self.parser.parse_html(current_html) returns a dict 
                # like game_state = {'my_player_data': ..., 'table_data': ..., 'all_players_data': ...}
                # or None/throws error on failure.
                parsed_state = self.parser.parse_html(current_html)
                
                if parsed_state and parsed_state.get('warnings'):
                    for warning in parsed_state['warnings']:
                        self.logger.warning(f"Parser Warning: {warning}")

                if not parsed_state or parsed_state.get('error'): # Check for error from parser
                    self.logger.error(f"Failed to parse HTML or critical data missing: {parsed_state.get('error', 'Unknown parsing error') if parsed_state else 'Parser returned None'}. Retrying in 1 second...")
                    time.sleep(1)
                    continue

                # Process the parsed HTML data using PokerBot's analyze method.
                # This populates self.table_data and self.player_data (which includes hand_evaluation).
                self.analyze()

                # Get data from PokerBot's attributes after analysis
                my_player_data = self.get_my_player()
                table_data = self.table_data
                all_players_data = self.player_data # self.player_data is the list of all player dicts

                # Check if essential data is present after analysis
                if not my_player_data or not table_data: # all_players_data is self.player_data
                    self.logger.warning("Essential game data missing after self.analyze(). Retrying in 1 second...")
                    time.sleep(1)
                    continue

                if my_player_data and my_player_data.get('has_turn'):
                    hand_rank_description = my_player_data.get('hand_evaluation', (0, "N/A"))[1]
                    # Enhanced logging for player's turn
                    bet_to_call_str = my_player_data.get('bet_to_call', '0') # Get bet_to_call from player data
                    bet_to_call_val = parse_currency_string(bet_to_call_str)
                    log_message = (
                        f"My turn. Hand: {my_player_data.get('cards')}, Rank: {hand_rank_description}, " 
                        f"Stack: {my_player_data.get('stack')}, Bet to call: {bet_to_call_val:.2f}"
                    )
                    self.logger.info(log_message)
                    self.logger.info(f"Pot: {table_data.get('pot_size')}, Community Cards: {table_data.get('community_cards')}")

                    action_tuple = self.decision_engine.make_decision(my_player_data, table_data, all_players_data)
                    
                    action = ""
                    amount = 0 # Default amount to 0

                    if isinstance(action_tuple, tuple) and len(action_tuple) == 2:
                        action, amount = action_tuple
                        if amount is None: # Ensure amount has a default if make_decision returns None for it
                            amount = 0
                    elif isinstance(action_tuple, str): # Should ideally not happen if make_decision is standardized
                        action = action_tuple
                        # If only action string is returned, it implies no specific amount (e.g. FOLD, CHECK)
                        # For CALL/RAISE, this path would be problematic if amount isn't part of a tuple.
                        # However, make_decision is expected to return (ACTION, amount)
                    else:
                        self.logger.warning(f"Warning: Unknown action format from decision engine: {action_tuple}")
                        action = ACTION_FOLD
                        amount = 0 # Ensure amount is 0 for FOLD

                    # Enhanced logging for decision
                    decision_log_message = f"Decision: {action}"
                    if amount is not None:
                        decision_log_message += f" Amount: {amount:.2f}" # Log amount with 2 decimal places
                    # Log the bet_to_call again here if it was a factor in a CALL decision, or just rely on the turn log.
                    # For RAISE and CALL, the 'amount' is the key part of the decision.
                    self.logger.info(decision_log_message)

                    if action == ACTION_FOLD:
                        self.ui_controller.action_fold()
                    elif action == ACTION_CHECK or action == ACTION_CALL:
                        # If the action is CALL and it's an all-in situation, 
                        # and the decision was to call the all-in, we might need a specific button click.
                        # The decision engine now returns `my_stack` as amount for all-in calls.
                        my_current_stack = parse_currency_string(my_player_data.get('stack', '0'))
                        
                        if action == ACTION_CALL and amount is not None and amount >= my_current_stack and my_player_data.get('is_all_in_call_available'):
                            self.logger.info("Performing All-in Call action.")
                            self.ui_controller.action_all_in() # Assumes action_all_in handles this specific click
                        else:
                            self.ui_controller.action_check_call()
                    elif action == ACTION_RAISE:
                        # If the raise amount is the player's entire stack, it's an all-in raise.
                        # The UI might have a dedicated all-in button for this instead of raise + amount.
                        my_current_stack = parse_currency_string(my_player_data.get('stack', '0'))
                        # Ensure amount is not None and is a number before comparison
                        if amount is not None and isinstance(amount, (int, float)) and my_current_stack <= amount: 
                             # Check if a dedicated all-in button is available from parser info (optional)
                            if 'all_in' in my_player_data.get('available_actions', []):
                                self.logger.info("Performing All-in action (raise all-in).")
                                self.ui_controller.action_all_in()
                            else:
                                self.logger.info("Performing Raise action (for all-in amount).")
                                self.ui_controller.action_raise(amount=amount) # Standard raise if no specific all-in button identified for this path
                        else:
                            self.ui_controller.action_raise(amount=amount)
                    else:
                        self.logger.warning(f"Unknown action: {action}")
                    
                    time.sleep(5) # Changed from 2 to 5 seconds
                else:
                    if my_player_data: # Successfully parsed, but not our turn
                         self.logger.info(f"Not my turn. My Hand: {my_player_data.get('cards')}. Waiting...")
                    else: # Should not happen if parsing check above is robust
                         self.logger.warning("Player data not found or not my turn. Waiting...")
                
                time.sleep(self.ui_controller.get_delay('main_loop_general_delay')) # Use configured delay

        except KeyboardInterrupt:
            self.logger.info("PokerBot stopped by user.")
        finally:
            self.running = False
            self.logger.info("PokerBot main_loop ended.")
            # self.close_logger() # Call close_logger here when main_loop finishes

if __name__ == "__main__":
    # Basic logging setup for the __main__ block, PokerBot will set up its own logger instance
    # Ensure the root logger also handles UTF-8 for any prints that might go through it,
    # though PokerBot class uses its own configured logger.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
        logging.FileHandler("poker_bot_main.log", mode='a', encoding='utf-8'), # Log main block to a separate file or same with different logger name
        logging.StreamHandler(sys.stdout) # Ensure console output from basicConfig also attempts to use sys.stdout
    ])
    logger = logging.getLogger(__name__) # Get a logger for the main block
    bot = None # Initialize bot to None
    try:
        if len(sys.argv) > 1 and sys.argv[1] == 'calibrate': # Added calibrate command
            bot = PokerBot()
            bot.run_calibration()
        elif len(sys.argv) > 1:
            file_path = sys.argv[1]
            bot = PokerBot()
            bot.run_test_file(file_path)
        else:
            bot = PokerBot()
            # Check if calibration is needed before starting the main loop for live play
            if not bot.ui_controller.positions:
                logger.warning("UI positions not calibrated. Please run calibration first or ensure config.json exists.")
                choice = input("Would you like to run calibration now? (yes/no): ").strip().lower()
                if choice == 'yes':
                    bot.run_calibration()
                else:
                    logger.info("Exiting. Please calibrate UI positions before running the bot.")
                    sys.exit()
            
            if not bot.ui_controller.positions.get("html_capture_point"): # Basic check
                logger.critical("HTML capture point not calibrated. Run calibration.")
                sys.exit()
            
            bot.main_loop()
    except Exception as e:
        logger.error(f"An error occurred in __main__: {e}", exc_info=True)
    finally:
        if bot:
            bot.close_logger()
        logger.info("PokerBot application finished.")

