"""
poker_bot_v2.py
A next-generation PokerBot using abstraction, CFR-based solver, and strategy lookup.
"""
import sys
import time
import logging
import threading
import json
import hashlib

from hand_abstraction import HandAbstraction
from cfr_solver import CFRSolver
from strategy_lookup import StrategyLookup
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator
from html_parser import PokerPageParser
from ui_controller import UIController
from decision_engine import ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE

def parse_currency_string(value_str):
    if isinstance(value_str, (int, float)):
        return float(value_str)
    if not isinstance(value_str, str):
        return 0.0
    cleaned_str = value_str.replace('€', '').replace('$', '').replace(',', '').strip()
    try:
        return float(cleaned_str)
    except ValueError:
        return 0.0

class PokerBotV2:
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.fh = None
        self.ch = None
        
        log_file_path = 'poker_bot_v2.log'
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        self.fh = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        self.fh.setLevel(logging.DEBUG)
        self.ch = logging.StreamHandler(sys.stdout)
        self.ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.fh.setFormatter(formatter)
        self.ch.setFormatter(formatter)
        
        self.logger.addHandler(self.fh)
        self.logger.addHandler(self.ch)
        self.logger.propagate = False

        self.config = config if config is not None else {}
        self.big_blind = self.config.get('big_blind', 0.04)
        self.small_blind = self.config.get('small_blind', 0.02)

        self.parser = PokerPageParser()
        self.ui_controller = UIController()
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = EquityCalculator()
        self.abstraction = HandAbstraction(self.hand_evaluator, self.equity_calculator)
        
        # Load the newly generated GPU-trained strategies
        self.logger.info("🚀 Loading GPU-trained strategies...")
        self.strategy_lookup = StrategyLookup()
        strategy_count = len(self.strategy_lookup.strategy_table)
        self.logger.info(f"✅ Loaded {strategy_count:,} GPU-generated strategies for optimal play!")
        
        if strategy_count > 100000:
            self.logger.info("🎯 MASSIVE STRATEGY DATABASE: Ultra-high-performance poker bot ready!")
        elif strategy_count > 10000:
            self.logger.info("🔥 HIGH-PERFORMANCE STRATEGY DATABASE: Advanced poker bot ready!")
        elif strategy_count > 1000:
            self.logger.info("⚡ GOOD STRATEGY DATABASE: Enhanced poker bot ready!")
        else:
            self.logger.warning(f"⚠️  Limited strategies ({strategy_count}). Consider running train_cfr.py for better performance.")
        
        self.cfr_solver = CFRSolver(self.abstraction, self.hand_evaluator, self.equity_calculator, logger_instance=self.logger)

        self.table_data = {}
        self.player_data = []
        self.running = False
        self.last_html_content = None
        self.starting_stack = 6
        
        # Strategy utilization tracking
        self.strategy_stats = {
            'gpu_strategies_used': 0,
            'cfr_fallbacks_used': 0,
            'total_decisions': 0
        }

    def close_logger(self):
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
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

    def __del__(self):
        self.close_logger()

    def analyze_table(self):
        self.table_data = self.parser.analyze_table()

    def analyze_players(self):
        self.player_data = self.parser.analyze_players()

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

    def decide_action(self):
        my_player = self.get_my_player()
        if not my_player or not my_player.get('has_turn'):
            return None, None

        # --- State Extraction for Hashing ---
        stage_map = {'preflop': 0, 'flop': 1, 'turn': 2, 'river': 3}
        stage_name = self.table_data.get('game_stage', 'preflop').lower()
        street = stage_map.get(stage_name, 0)

        # --- RELATIVE TURN INDEX CALCULATION (Critical for hash matching) ---
        # The strategy is stored based on the order of action, not the seat number.
        # We must calculate our index (0, 1, 2...) in the current round's betting order.

        active_players = [p for p in self.player_data if not p.get('is_empty') and 'Fold' not in p.get('status', '')]
        is_heads_up = len(active_players) == 2
        
        # Get the dealer seat directly from the parsed table data, using the correct key 'dealer_position'.
        dealer_position_str = self.table_data.get('dealer_position')

        if dealer_position_str is None or dealer_position_str == "N/A":
            self.logger.error("Cannot determine turn order without dealer position from table_data. Folding.")
            return ACTION_FOLD, 0

        try:
            dealer_seat = int(dealer_position_str)
        except (ValueError, TypeError):
            self.logger.error(f"Could not parse dealer position '{dealer_position_str}' to an integer. Folding.")
            return ACTION_FOLD, 0

        # Sort players by action order. This is the critical fix.
        if street == 0 and is_heads_up:
            # Preflop Heads-Up: The dealer (button) acts FIRST.
            # We sort so the dealer has index 0 and the other player has index 1.
            self.logger.debug("Applying preflop heads-up turn order logic.")
            ordered_players = sorted(active_players, key=lambda p: 0 if int(p['seat']) == dealer_seat else 1)
        else:
            # Standard Order (Postflop OR 3+ players preflop): Action starts to the left of the dealer.
            self.logger.debug("Applying standard turn order logic.")
            num_seats = len(self.player_data)
            # The key for sorting is `(seat - dealer_seat - 1 + num_seats) % num_seats`.
            # This creates a sequence where the player after the dealer is first.
            ordered_players = sorted(active_players, key=lambda p: (int(p['seat']) - dealer_seat - 1 + num_seats) % num_seats)

        # Find the index of our player in this ordered list.
        turn_index = -1
        for i, p in enumerate(ordered_players):
            if p.get('is_my_player', False):
                turn_index = i
                break

        if turn_index == -1:
            self.logger.error("Could not determine my turn index. The bot may have folded or is not in the hand. Folding.")
            return ACTION_FOLD, 0

        max_bet = 0.0
        total_bets = 0.0
        for p in self.player_data:
            player_bet = parse_currency_string(p.get('bet', '0'))
            total_bets += player_bet
            if player_bet > max_bet:
                max_bet = player_bet
        
        pot_size = parse_currency_string(self.table_data.get('pot_size', '0'))

        # CRITICAL: The hash must match the training environment.
        # The trainer's view of the pot is the total amount of money committed,
        # which is the pot displayed on the table PLUS all bets made in the current round.
        effective_pot = pot_size + total_bets

        # --- Hash Generation (must match gpu_cfr_trainer.py ENHANCED version) ---
        # Enhanced hash to match the trainer's diverse hash computation
        num_active = sum(1 for p in self.player_data if not p.get('is_empty') and 'Fold' not in p.get('status', ''))
        avg_bet = total_bets / len(self.player_data) if len(self.player_data) > 0 else 0
        
        street_component = street * 10000000000
        player_component = turn_index * 1000000000
        maxbet_component = int(round(float(max_bet), 2) * 100) * 100000
        pot_component = int(round(float(effective_pot), 2) * 100) * 10
        active_component = num_active * 1000000
        avgbet_component = int(round(float(avg_bet), 2) * 100)
        
        # Enhanced hash combination matching the trainer
        combined_hash = (street_component + player_component + maxbet_component + 
                        pot_component + active_component + avgbet_component)
        
        # Apply the same enhanced mixing as the trainer
        combined_hash = combined_hash * 2654435761  # Large prime
        combined_hash = combined_hash ^ (combined_hash >> 16)  # XOR folding
        combined_hash = combined_hash * 1664525  # Another prime
        combined_hash = combined_hash ^ (combined_hash >> 24)  # More folding
        combined_hash = combined_hash & 0x7FFFFFFFFFFFFFFF  # Ensure positive
        
        info_hash = combined_hash
        state_tuple = (street, turn_index, round(float(max_bet), 2), round(float(effective_pot), 2), num_active, round(float(avg_bet), 2))
        self.logger.info(f"Generated stable info hash: {info_hash} for state {state_tuple}")

        # Prepare state components for fuzzy matching fallback
        state_components = {
            'street': street,
            'turn_index': turn_index,
            'max_bet': round(float(max_bet), 2),
            'effective_pot': round(float(effective_pot), 2),
            'num_active': num_active,
            'avg_bet': round(float(avg_bet), 2)
        }

        # 1. Try to get a strategy using exact match, then fuzzy matching if needed
        strategy, match_type = self.strategy_lookup.get_strategy_with_fuzzy_fallback(info_hash, state_components)
        
        if strategy:
            if match_type == 'exact':
                self.logger.info(f"🎯 Using exact GPU-trained strategy for hash {info_hash}")
                self.strategy_stats['gpu_strategies_used'] += 1
            elif match_type == 'fuzzy':
                self.logger.info(f"🔍 Using fuzzy-matched GPU-trained strategy for hash {info_hash}")
                self.strategy_stats['gpu_strategies_used'] += 1
            elif match_type == 'component':
                self.logger.info(f"🔧 Using component-matched GPU-trained strategy for hash {info_hash}")
                self.strategy_stats['gpu_strategies_used'] += 1
        else:
            # 2. If no match found (exact or fuzzy), run a quick CFR solve for this spot
            self.logger.info(f"🔍 No precomputed strategy found for hash {info_hash}. Running real-time CFR solve.")
            
            player_hole_cards = my_player.get('cards', [])
            if not player_hole_cards:
                self.logger.warning("Cannot decide action without hole cards.")
                return ACTION_FOLD, 0

            community_cards = self.table_data.get('community_cards', [])
            actions = my_player.get('available_actions', [ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE])
            num_opponents = sum(1 for p in self.player_data if not p.get('is_my_player', False) and not p.get('is_empty', False))

            strategy = self.cfr_solver.solve(player_hole_cards, community_cards, effective_pot, actions, stage_name, num_opponents)
            self.logger.info(f"🧠 CFR computed strategy: {strategy}")
            self.strategy_stats['cfr_fallbacks_used'] += 1
        
        # Update total decisions and log stats periodically
        self.strategy_stats['total_decisions'] += 1
        if self.strategy_stats['total_decisions'] > 0 and self.strategy_stats['total_decisions'] % 10 == 0:
            gpu_usage_rate = (self.strategy_stats['gpu_strategies_used'] / self.strategy_stats['total_decisions']) * 100
            self.logger.info(f"📈 Strategy Usage: {gpu_usage_rate:.1f}% GPU-trained, {100-gpu_usage_rate:.1f}% CFR fallback ({self.strategy_stats['total_decisions']} total decisions)")

        if not strategy:
            self.logger.error("Failed to determine a strategy. Folding as a fallback.")
            return ACTION_FOLD, 0

        # 3. Pick the action with the highest probability
        # The strategy from the JSON file has keys like 'action_0', 'action_1', etc.
        # We need to map these back to our action constants.
        action_map = {
            'action_0': ACTION_FOLD,
            'action_1': ACTION_CALL, # Or Check
            'action_2': ACTION_RAISE, # 33% pot raise
            'action_3': ACTION_RAISE, # 66% pot raise
            'action_4': ACTION_RAISE, # 100% pot raise
            'action_5': ACTION_RAISE  # All-in
        }
        
        # Store original strategy for raise size analysis
        original_strategy = strategy.copy()
        
        # Handle both strategy formats (from JSON and from CFR solver)
        if any(k in action_map for k in strategy.keys()):
             # Remap action names if they are in 'action_x' format
            strategy = {action_map.get(k, k): v for k, v in strategy.items()}

        # Ensure CHECK is handled correctly if CALL is not available
        available_actions = my_player.get('available_actions', [])
        if ACTION_CHECK in available_actions and ACTION_CALL not in available_actions:
            if ACTION_CALL in strategy:
                strategy[ACTION_CHECK] = strategy.pop(ACTION_CALL)

        # For raise actions, combine all raise probabilities and choose sizing
        total_raise_prob = 0
        raise_size_probs = {}
        
        # Extract individual raise action probabilities from original strategy
        for action_key, prob in original_strategy.items():
            if action_key.startswith('action_'):
                action_num = int(action_key.split('_')[1])
                if action_num >= 2:  # Raise actions (2, 3, 4, 5)
                    if action_num == 2:
                        raise_size_probs['small'] = prob  # 33% pot
                    elif action_num == 3:
                        raise_size_probs['medium'] = prob  # 66% pot
                    elif action_num == 4:
                        raise_size_probs['large'] = prob  # 100% pot
                    elif action_num == 5:
                        raise_size_probs['allin'] = prob  # All-in
                    total_raise_prob += prob

        # Create simplified strategy for action selection using original keys
        simple_strategy = {}
        if 'action_0' in original_strategy:
            simple_strategy[ACTION_FOLD] = original_strategy['action_0']
        if 'action_1' in original_strategy:
            simple_strategy[ACTION_CALL] = original_strategy['action_1']
        if total_raise_prob > 0:
            simple_strategy[ACTION_RAISE] = total_raise_prob

        # Filter strategy to only include available actions
        available_strategy = {a: p for a, p in simple_strategy.items() if a in available_actions}
        if not available_strategy:
            self.logger.error(f"No valid actions from strategy {simple_strategy} match available actions {available_actions}. Folding.")
            return ACTION_FOLD, 0

        best_action = max(available_strategy.items(), key=lambda x: x[1])[0]
        
        # Choose raise size based on individual action probabilities
        chosen_raise_size = "medium"  # default
        if best_action == ACTION_RAISE and raise_size_probs:
            chosen_raise_size = max(raise_size_probs.items(), key=lambda x: x[1])[0]
        
        self.logger.info(f"Bot decision: {best_action} (strategy: {available_strategy}, raise_size: {chosen_raise_size})")

        # 4. Determine amount
        amount = 0
        if best_action == ACTION_RAISE:
            # Choose raise amount based on the selected raise size
            if chosen_raise_size == 'small':
                amount = effective_pot * 0.33
            elif chosen_raise_size == 'medium':
                amount = effective_pot * 0.66
            elif chosen_raise_size == 'large':
                amount = effective_pot * 1.0
            elif chosen_raise_size == 'allin':
                my_stack = parse_currency_string(my_player.get('stack', '0'))
                amount = my_stack
            else:
                amount = effective_pot * 0.75  # fallback
        elif best_action == ACTION_CALL:
            amount = parse_currency_string(my_player.get('bet_to_call', '0'))

        return best_action, amount

    def test_from_file(self, file_path):
        self.logger.info(f"--- Running Test from File: {file_path} ---")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_html = f.read()
            
            self.last_html_content = current_html
            parsed_state = self.parser.parse_html(current_html)
            
            if not parsed_state or parsed_state.get('error'):
                self.logger.error(f"Failed to parse HTML from {file_path}: {parsed_state.get('error', 'Unknown') if parsed_state else 'None'}")
                return

            self.analyze()
            my_player = self.get_my_player()

            if my_player and my_player.get('has_turn'):
                self.logger.info("My turn to act.")
                action, amount = self.decide_action()
                if action:
                    self.logger.info(f"Decision: {action}, Amount: {amount}")
                else:
                    self.logger.warning("Could not determine an action.")
            else:
                self.logger.info("Not my turn or no active player found in test file.")

        except FileNotFoundError:
            self.logger.error(f"Test file not found: {file_path}")
        except Exception as e:
            self.logger.error(f"An error occurred during test_from_file: {e}", exc_info=True)

    def start_kill_switch_listener(self):
        try:
            import keyboard
        except ImportError:
            self.logger.warning("'keyboard' library not found. Kill switch disabled.")
            return
        def listen():
            keyboard.wait('ctrl+q')
            self.logger.info("Ctrl+Q detected. Stopping bot.")
            self.running = False
        t = threading.Thread(target=listen, daemon=True)
        t.start()

    def main_loop(self):
        self.running = True
        self.start_kill_switch_listener()
        
        # Display enhanced startup message
        strategy_count = len(self.strategy_lookup.strategy_table)
        self.logger.info("🚀 PokerBotV2 ULTRA-PERFORMANCE EDITION started!")
        self.logger.info(f"🎯 Armed with {strategy_count:,} GPU-trained strategies")
        self.logger.info("⚡ Ready for optimal poker play. Press Ctrl+Q to stop.")
        
        if strategy_count > 100000:
            self.logger.info("🔥 ULTRA-HIGH-PERFORMANCE MODE: Massive strategy database loaded!")
        
        if not self.ui_controller.positions:
            self.logger.warning("UI positions not calibrated. Please run calibration first.")
            return

        try:
            while self.running:
                self.logger.info("\n--- New Decision Cycle ---")
                current_html = self.ui_controller.get_html_from_screen_with_auto_retry()

                if not current_html:
                    self.logger.warning("Failed to retrieve HTML. Retrying...")
                    time.sleep(1)
                    continue
                
                self.last_html_content = current_html
                parsed_state = self.parser.parse_html(current_html)
                
                if not parsed_state or parsed_state.get('error'):
                    self.logger.error(f"Failed to parse HTML: {parsed_state.get('error', 'Unknown') if parsed_state else 'None'}. Retrying...")
                    time.sleep(1)
                    continue

                self.analyze()
                my_player = self.get_my_player()

                if my_player and my_player.get('has_turn'):
                    self.logger.info("My turn to act.")
                    action, amount = self.decide_action()

                    if action:
                        self.logger.info(f"Decision: {action}, Amount: {amount}")
                        if action == ACTION_FOLD:
                            self.ui_controller.action_fold()
                        elif action == ACTION_CHECK or action == ACTION_CALL:
                            self.ui_controller.action_check_call()
                        elif action == ACTION_RAISE:
                            self.ui_controller.action_raise(amount)
                        time.sleep(self.config.get('delays', {}).get('after_action_delay', 5.0))
                    else:
                        self.logger.warning("Could not determine an action. Waiting.")
                else:
                    self.logger.info("Not my turn. Waiting...")
                
                time.sleep(self.config.get('delays', {}).get('main_loop_general_delay', 0.25))

        except KeyboardInterrupt:
            self.logger.info("PokerBot stopped by user.")
        finally:
            self.running = False
            self.logger.info("PokerBot main_loop ended.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    bot = None
    try:
        bot = PokerBotV2()
        
        # --- TESTING FROM FILE ---
        # To run a test, uncomment the following lines and provide the path to your HTML file.
        # Make sure to comment out or skip the main_loop if you are just testing.
        test_file_path = 'examples/preflop_my_turn.html'
        bot.test_from_file(test_file_path)
        
        # --- NORMAL EXECUTION ---
        # if not bot.ui_controller.positions:
        #     logger.critical("UI positions not calibrated. Run the original poker_bot.py with 'calibrate' argument first.")
        #     sys.exit()
        # bot.main_loop()

    except Exception as e:
        logger.error(f"An error occurred in __main__: {e}", exc_info=True)
    finally:
        if bot:
            bot.close_logger()
        logger.info("PokerBotV2 application finished.")
