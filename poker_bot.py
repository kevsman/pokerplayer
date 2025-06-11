from bs4 import BeautifulSoup
import re
import sys
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator
from opponent_tracking import OpponentTracker # Ensure OpponentTracker is imported
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE # Import actions
from ui_controller import UIController
from config import Config # Import Config
from html_parser import PokerPageParser # Add this import
import time
import logging

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
    def __init__(self, config_path='config.json'):
        self.config = Config(config_path) # Use Config class
        self.logger = self._setup_logger()
        self.parser = PokerPageParser(self.logger, self.config)
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = EquityCalculator()
        # Initialize OpponentTracker with config
        self.opponent_tracker = OpponentTracker(config=self.config, logger=self.logger)
        # Pass config to DecisionEngine
        self.decision_engine = DecisionEngine(self.hand_evaluator, self.equity_calculator, self.opponent_tracker, self.config, self.logger)
        self.ui_controller = UIController(self.logger, self.config) # Pass config
        self.table_data = {}
        self.player_data = [] # This will store list of player dicts
        self.current_html_content = ""
        self.last_html_content = ""
        self.consecutive_unchanged_reads = 0
        self.is_test_mode = False # Flag for test mode
        self.test_file_path = None # Path for test file
        self.action_history = [] # Initialize action history for the current hand
        self.current_hand_id_for_history = None # To track hand changes for resetting history
        # self.big_blind and self.small_blind are already set from config or defaults
        self.running = False

    def _setup_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('poker_bot.log', mode='a', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        
        # Configure formatter to handle Unicode characters
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Set encoding for StreamHandler to handle Unicode on Windows
        if hasattr(ch, 'stream') and hasattr(ch.stream, 'reconfigure'):
            try:
                ch.stream.reconfigure(encoding='utf-8')
            except Exception:
                # Fallback: create a new StreamHandler with proper encoding
                import io
                if sys.platform.startswith('win'):
                    # For Windows, wrap stdout to handle Unicode properly
                    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                    ch = logging.StreamHandler(utf8_stdout)
                    ch.setLevel(logging.INFO)
                    ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        logger.propagate = False # Prevent logging to root logger if it has handlers

        return logger

    def close_logger(self):
        """Close all logging handlers."""
        # Check if logger was initialized and has handlers
        if hasattr(self, 'logger') and self.logger and self.logger.hasHandlers():
            self.logger.info("Closing logger handlers.")
            if self.fh:
                self.fh.close()
                self.logger.removeHandler(self.fh)
                self.fh = None
            if self.ch:
                self.ch.close()
                self.logger.removeHandler(self.ch)
                self.ch = None
            # Also clear any other handlers that might have been added
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
        elif hasattr(self, 'fh') and self.fh: # Fallback for fh if logger is not fully set
            self.fh.close()
            self.fh = None
        elif hasattr(self, 'ch') and self.ch: # Fallback for ch if logger is not fully set
            self.ch.close()
            self.ch = None

    def __del__(self):
        """Ensure logger is closed when bot instance is deleted."""
        self.close_logger()

    def analyze_table(self):
        self.table_data = self.parser.analyze_table()

    def analyze_players(self):
        self.player_data = self.parser.analyze_players() 
        
        community_cards_for_equity = self.table_data.get('community_cards', [])
        # Ensure community_cards_for_equity are in the string format EquityCalculator expects, if not already.
        # Assuming parser already provides them as list of strings like ['Ah', 'Ks']

        for player_info in self.player_data:
            player_hole_cards = player_info.get('cards')
            
            if player_info.get('is_my_player') and player_hole_cards:
                # Calculate hand evaluation (rank, description)
                player_info['hand_evaluation'] = self.hand_evaluator.calculate_best_hand(player_hole_cards, community_cards_for_equity)
                player_info['hand_rank'] = player_info['hand_evaluation'][1] 

                # Calculate win probability using EquityCalculator
                # For simplicity in this test, assume 1 opponent and a default number of simulations.
                # opponent_range_str_list might be complex; for now, let EquityCalculator handle default/random if applicable.
                # EquityCalculator.calculate_equity_monte_carlo expects hole_cards_str_list as a list of lists,
                # e.g., [['Ah', 'Qh']] for one player.
                
                # Correctly format hole_cards for EquityCalculator:
                formatted_hole_cards = [player_hole_cards] if player_hole_cards else []

                if formatted_hole_cards:
                    # Using a simplified call for now, assuming 1 opponent, random range.
                    # The EquityCalculator's current implementation of calculate_equity_monte_carlo
                    # might need adjustment if opponent_range_str_list is strictly required or
                    # if it doesn't handle a "random" opponent by default.
                    # For now, passing None for opponent_range and a fixed number of simulations.
                    win_prob, tie_prob, equity = self.equity_calculator.calculate_equity_monte_carlo(
                        formatted_hole_cards, 
                        community_cards_for_equity, 
                        None, # opponent_range_str_list - assuming None means random or default
                        num_simulations=5000 # A reasonable number for faster testing
                    )
                    player_info['win_probability'] = win_prob
                    player_info['tie_probability'] = tie_prob # Store tie_prob as well
                    # self.logger.debug(f"Calculated equity for {player_info.get('name')}: Win={win_prob:.2f}, Tie={tie_prob:.2f}")
                else:
                    player_info['win_probability'] = 0.0 # Default if no hole cards
                    player_info['tie_probability'] = 0.0
                    # self.logger.debug(f"No hole cards for {player_info.get('name')} to calculate equity.")

            elif not player_info.get('is_my_player') and player_info.get('has_hidden_cards'):
                player_info['hand_rank'] = "N/A (Hidden Cards)"
                player_info['hand_evaluation'] = (0, "N/A (Hidden Cards)", []) # Default eval for others
                player_info['win_probability'] = 0.0 # Cannot calculate for hidden cards
                player_info['tie_probability'] = 0.0
            else:
                player_info['hand_rank'] = "N/A"
                player_info['hand_evaluation'] = (0, "N/A", []) # Default eval for empty/no cards
                player_info['win_probability'] = 0.0
                player_info['tie_probability'] = 0.0


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
          # Show only essential player info - my player and active player
        my_player = self.get_my_player()
        active_player = self.get_active_player()
        
        if my_player:
            summary.append("\n--- My Player ---")
            hand_rank_str = my_player.get('hand_rank', 'N/A')
            cards_text = f" Cards: {' '.join(my_player.get('cards', []))}" if my_player.get('cards') else ""
            hand_text = f" Hand: {hand_rank_str}" if hand_rank_str and hand_rank_str != 'N/A' else ""
            summary.append(f"  Seat {my_player.get('seat', 'N/A')}: {my_player.get('name', 'N/A')} - Stack: {my_player.get('stack', 'N/A')}, Bet: {my_player.get('bet', '0')}{cards_text}{hand_text}")
        
        # Count total active players
        active_players_count = len([p for p in self.player_data if not p.get('is_empty', False)])
        summary.append(f"\n--- Players: {active_players_count} active ---")        
        active_player = self.get_active_player()
        if active_player:
            summary.append(f"It is currently Seat {active_player['seat']} ({active_player['name']})'s turn.")
        else:
            summary.append("No player currently has the turn (or turn detection failed).")
            
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

            self.logger.info("\\n--- Game Summary from Test File ---")
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

                # Find my_player_index
                my_player_index = -1
                for i, p_data in enumerate(all_players_data):
                    # Assuming 'name' and 'seat' are reliable identifiers, or a unique ID if available
                    if p_data.get('name') == my_player_data.get('name') and p_data.get('seat') == my_player_data.get('seat'):
                        my_player_index = i
                        break
                
                if my_player_index == -1:
                    self.logger.error("Could not find my_player_index in all_players_data for test file run.")
                    return ACTION_FOLD, 0

                # Construct game_state for DecisionEngine
                # Ensure player data has 'hand' key for cards
                processed_players_data = []
                for p_data in all_players_data:
                    p_copy = p_data.copy()
                    if 'cards' in p_copy and 'hand' not in p_copy:
                        p_copy['hand'] = p_copy['cards']
                    elif 'hand' not in p_copy: # Ensure hand key exists even if no cards (e.g. for opponents)
                        p_copy['hand'] = []
                    processed_players_data.append(p_copy)

                game_state_for_decision = {
                    # "players": all_players_data, # PokerPageParser now returns 'all_players_data'
                    "players": processed_players_data, # Use processed data
                    "pot_size": table_data.get('pot_size'),
                    "community_cards": table_data.get('community_cards'),
                    "current_round": table_data.get('game_stage', 'preflop').lower(), # Ensure current_round is present
                    "big_blind": self.config.get('big_blind'),
                    "small_blind": self.config.get('small_blind'),
                    "min_raise": self.config.get('big_blind', 0.02) * 2, # Ensure min_raise
                    # 'board' and 'street' are often aliases or similar to community_cards and current_round
                    "board": table_data.get('community_cards'), 
                    "street": table_data.get('game_stage', 'preflop').lower()
                }

                # action_tuple = self.decision_engine.make_decision(my_player_data, table_data, all_players_data)
                action_tuple = self.decision_engine.make_decision(game_state_for_decision, my_player_index)
                
                action = ""
                amount = 0 

                if isinstance(action_tuple, tuple) and len(action_tuple) == 2:
                    action, amount = action_tuple
                    if amount is None: 
                        amount = 0
                elif isinstance(action_tuple, str): 
                    action = action_tuple
                    amount = 0 # Initialize amount if action_tuple is a string
                else:
                    self.logger.warning(f"Warning: Unknown action format from decision engine: {action_tuple}")
                    action = ACTION_FOLD # Default to FOLD
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
        """Close all logging handlers."""
        # Check if logger was initialized and has handlers
        if hasattr(self, 'logger') and self.logger and self.logger.hasHandlers():
            self.logger.info("Closing logger handlers.")
            if self.fh:
                self.fh.close()
                self.logger.removeHandler(self.fh)
                self.fh = None
            if self.ch:
                self.ch.close()
                self.logger.removeHandler(self.ch)
                self.ch = None
            # Also clear any other handlers that might have been added
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
        elif hasattr(self, 'fh') and self.fh: # Fallback for fh if logger is not fully set
            self.fh.close()
            self.fh = None
        elif hasattr(self, 'ch') and self.ch: # Fallback for ch if logger is not fully set
            self.ch.close()
            self.ch = None

    def main_loop(self):
        self.logger.info("Poker Bot - Main Loop Started")
        try:
            while True:
                self.logger.info("\n--- New Decision Cycle ---")
                self.logger.debug("Attempting to retrieve game HTML from screen...")
                current_html = self.ui_controller.get_html_from_screen_with_auto_retry()
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

                # Check for hand change to reset action_history
                new_hand_id = self.table_data.get('hand_id')
                if new_hand_id and new_hand_id != self.current_hand_id_for_history:
                    self.logger.info(f"New hand detected (ID: {new_hand_id}). Resetting action history.")
                    self.action_history = []
                    self.current_hand_id_for_history = new_hand_id
                elif not new_hand_id and self.current_hand_id_for_history: # Hand ended, no new ID yet
                    self.logger.info(f"Hand ID no longer present (was {self.current_hand_id_for_history}). Resetting action history.")
                    self.action_history = []
                    self.current_hand_id_for_history = None

                # Get opponent actions from parser and update history
                if hasattr(self.parser, 'get_parsed_actions') and callable(getattr(self.parser, 'get_parsed_actions')):
                    # Pass current HTML to get_parsed_actions for re-parsing if necessary
                    parsed_actions = self.parser.get_parsed_actions(html_content_for_reparse=current_html)
                    if parsed_actions:
                        for pa_action in parsed_actions:
                            # Basic deduplication: check if a similar action from the same player on the same street is already in recent history
                            is_duplicate = False
                            # Check a bit more than just the number of newly parsed actions to catch recent duplicates
                            # Check against the last N actions, where N is, for example, number of active players + a buffer
                            # This helps avoid re-adding actions if parsing is slightly delayed or re-triggered.
                            # The sequence number in action_history could also be used for more robust deduplication.
                            # For now, a simple check against recent history by content.
                            check_depth = len(self.player_data) + 3 # Check depth based on number of players + buffer
                            for recent_action in self.action_history[-check_depth:]:
                                if (recent_action.get('player_id') == pa_action.get('player_id') and
                                    recent_action.get('street') == pa_action.get('street') and
                                    recent_action.get('action_type') == pa_action.get('action_type') and
                                    recent_action.get('amount') == pa_action.get('amount') and
                                    not recent_action.get('is_bot')): # Only deduplicate opponent actions
                                    is_duplicate = True
                                    break
                            if not is_duplicate:
                                # Add hand_id to the parsed action before appending
                                pa_action['hand_id'] = self.current_hand_id_for_history
                                pa_action['sequence'] = len(self.action_history) # Add sequence number
                                self.action_history.append(pa_action)
                                self.logger.info(f"Added parsed opponent action to history: {pa_action}")
                                if self.opponent_tracker:
                                    # Ensure all necessary parameters are passed to log_action
                                    self.opponent_tracker.log_action(
                                        player_name=pa_action.get('player_id'), # Changed from player_id to player_name
                                        action=pa_action.get('action_type'),
                                        street=pa_action.get('street'),
                                        position=pa_action.get('position', 'unknown'), # Add position if available
                                        bet_size=pa_action.get('amount', 0),
                                        # pot_size needs to be the pot size *before* this action.
                                        # This might require more sophisticated state tracking or for parser to provide it.
                                        # For now, we might pass the current pot_size from table_data, though it's not ideal.
                                        pot_size=self.table_data.get('pot_size', 0), 
                                        hand_id=self.current_hand_id_for_history
                                    )
                            else:
                                self.logger.debug(f"Skipped adding duplicate parsed opponent action: {pa_action}")


                my_player_data = self.get_my_player()
                raw_all_players_data = self.parser.analyze_players() # Make sure this is called to get player data

                if my_player_data and my_player_data.get('has_turn'):
                    self.logger.info("My turn to act.")
                    # ... (logging hand info, stack, etc.) ...

                    processed_players_list = []
                    for p_orig in raw_all_players_data:
                        p_copy = p_orig.copy()
                        if 'hand' not in p_copy and 'cards' in p_copy:
                            p_copy['hand'] = p_copy['cards']
                        elif 'hand' not in p_copy:
                            p_copy['hand'] = []
                        if 'position' not in p_copy or not p_copy['position']:
                            p_copy['position'] = self.parser.get_player_position(p_copy.get('seat'), len(raw_all_players_data)) \
                                                if hasattr(self.parser, 'get_player_position') else f"Seat_{p_copy.get('seat', 'N/A')}"
                        processed_players_list.append(p_copy)
                    
                    my_player_index = -1
                    my_player_id_for_index = my_player_data.get('id')
                    for i, p_proc_data in enumerate(processed_players_list):
                        if p_proc_data.get('id') == my_player_id_for_index:
                            my_player_index = i
                            processed_players_list[i]['has_turn'] = True
                            break
                    
                    if my_player_index == -1:
                        self.logger.error("Could not find my_player_index in processed_players_list.")
                        action_tuple = (ACTION_FOLD, 0)
                    else:
                        game_state_for_decision = {
                            "players": processed_players_list,
                            "pot_size": self.table_data.get('pot_size'),
                            "community_cards": self.table_data.get('community_cards'),
                            "current_round": self.table_data.get('street', self.table_data.get('game_stage', 'preflop')).lower(),
                            "big_blind": self.config.get('big_blind'),
                            "small_blind": self.config.get('small_blind'),
                            "min_raise": self.config.get('big_blind') * 2,
                            "board": self.table_data.get('community_cards'),
                            "action_history": self.action_history
                        }
                        action_tuple = self.decision_engine.make_decision(game_state_for_decision, my_player_index)

                    action = ""
                    amount = 0
                    if isinstance(action_tuple, tuple) and len(action_tuple) == 2:
                        action, amount = action_tuple
                        if amount is None: amount = 0
                    elif isinstance(action_tuple, str):
                        action = action_tuple
                        amount = 0
                    else:
                        self.logger.warning(f"Warning: Unknown action format from decision engine: {action_tuple}")
                        action = ACTION_FOLD
                        amount = 0

                    decision_log_message = f"Decision: {action}"
                    if amount is not None and action != ACTION_FOLD and action != ACTION_CHECK : # Only log amount if relevant
                        decision_log_message += f" Amount: {amount:.2f}"
                    self.logger.info(decision_log_message)

                    if action == ACTION_FOLD:
                        self.ui_controller.action_fold()
                    elif action == ACTION_CHECK or action == ACTION_CALL:
                        # ... (existing logic for all_in_call_available)
                        my_current_stack_for_call = self.parser.parse_monetary_value(my_player_data.get('stack', '0'))
                        if action == ACTION_CALL and amount is not None and amount >= my_current_stack_for_call and my_player_data.get('is_all_in_call_available'):
                            self.logger.info("Performing All-in Call action.")
                            self.ui_controller.action_all_in()
                        else:
                            self.ui_controller.action_check_call()
                    elif action == ACTION_RAISE:
                        # ... (existing logic for all_in raise) ...
                        my_current_stack_for_raise = self.parser.parse_monetary_value(my_player_data.get('stack', '0'))
                        if amount is not None and isinstance(amount, (int, float)) and my_current_stack_for_raise <= amount:
                            self.logger.info("Performing All-in Raise action.")
                            self.ui_controller.action_all_in()
                        else:
                            self.ui_controller.action_raise(amount)
                    else:
                        self.logger.warning(f"Unknown action type: {action}. Performing FOLD.")
                        self.ui_controller.action_fold()

                    current_street_for_history = self.table_data.get('game_stage', self.table_data.get('street', 'preflop')).lower()
                    bot_player_id = "HeroBot"
                    if my_player_data and my_player_data.get('name'):
                        bot_player_id = my_player_data.get('name')
                    
                    bot_action_record = {
                        "player_id": bot_player_id,
                        "action_type": action.upper(),
                        "amount": float(amount) if amount is not None else 0.0,
                        "street": current_street_for_history,
                        "is_bot": True,
                        "sequence": len(self.action_history),
                        "hand_id": self.current_hand_id_for_history # Add hand_id to bot's actions
                    }
                    
                    # Avoid adding duplicate bot action
                    # Check only the very last action, and ensure it's for the current hand and street
                    is_recent_bot_action_same = False
                    if self.action_history: 
                        last_recorded_action = self.action_history[-1]
                        if (last_recorded_action.get('is_bot') and 
                            last_recorded_action.get('hand_id') == self.current_hand_id_for_history and
                            last_recorded_action.get('street') == current_street_for_history and 
                            last_recorded_action.get('action_type') == action.upper()):
                            is_recent_bot_action_same = True

                    if not is_recent_bot_action_same:
                        self.action_history.append(bot_action_record)
                        self.logger.info(f"Recorded bot action to action_history: {bot_action_record}")
                        if self.opponent_tracker and my_player_data:
                            self.opponent_tracker.log_action(
                                player_name=bot_player_id, # Changed from player_id to player_name
                                action=action.upper(),
                                street=current_street_for_history,
                                bet_size=float(amount) if amount is not None else 0.0,
                                # Position and pot_size for bot's own action might also need careful consideration
                                # For now, using basic values or 'unknown' if not readily available.
                                position=my_player_data.get('position', 'unknown'),
                                pot_size=self.table_data.get('pot_size', 0), # Pot size before bot's action might be more accurate
                                hand_id=self.current_hand_id_for_history
                            )
                    
                    time.sleep(self.config.get('delays', {}).get('after_action_delay', 5.0))

                else: # Not my turn or no player data
                    active_player = self.get_active_player() # This method might need raw_all_players_data
                    if active_player:
                        self.logger.info(f"Not my turn. Active player: {active_player.get('name')}. Waiting...")
                    elif my_player_data: # My player data exists, but not my turn
                        self.logger.info("Not my turn, but my player data exists. Waiting...")
                        # ... (existing logging for opponent stacks) ...
                    else: # No player data at all (e.g. observing, or error)
                        self.logger.info("No player data found or not my turn. Waiting...")
                
                time.sleep(self.config.get('delays', {}).get('main_loop_delay', 1.0))

        except KeyboardInterrupt:
            self.logger.info("Poker Bot stopped by user (KeyboardInterrupt).")
        except Exception as e:
            self.logger.error(f"Critical error in main loop: {e}", exc_info=True)
        finally:
            self.logger.info("Poker Bot - Main Loop Ended")

if __name__ == "__main__":
    # Basic logging setup for the __main__ block with Unicode support
    import io
    
    # Create Unicode-safe console handler for Windows
    console_handler = logging.StreamHandler()
    if sys.platform.startswith('win'):
        try:
            # Try to reconfigure stdout encoding
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            # Fallback: wrap stdout for Unicode support
            try:
                utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                console_handler = logging.StreamHandler(utf8_stdout)
            except Exception:
                # Final fallback: just use regular StreamHandler
                console_handler = logging.StreamHandler(sys.stdout)
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
        logging.FileHandler("poker_bot_main.log", mode='a', encoding='utf-8'),
        console_handler
    ])
    logger = logging.getLogger(__name__)
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

