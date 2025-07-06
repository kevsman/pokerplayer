"""
poker_bot_v2.py
A next-generation PokerBot using abstraction, Monte Carlo solver, and strategy lookup.
"""
import sys
import time
import logging
import threading
import json
import hashlib

from hand_abstraction import HandAbstraction
from monte_carlo_solver import MonteCarloSolver
from realtime_cfr_solver import RealTimeCFRSolver
from safe_strategy_lookup import SafeStrategyLookup
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator  # Use GPU equity calculator
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
        self.equity_calculator = GPUEquityCalculator(use_gpu=True)  # Use GPU equity calculator
        self.abstraction = HandAbstraction(self.hand_evaluator, self.equity_calculator)
        
        # Load the newly generated GPU-trained strategies
        self.logger.info("🚀 Loading GPU-trained strategies...")
        self.strategy_lookup = SafeStrategyLookup()
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
        
        self.monte_carlo_solver = MonteCarloSolver(self.abstraction, self.hand_evaluator, self.equity_calculator, logger_instance=self.logger)
        
        # Initialize the real-time CFR solver for advanced fallback
        self.logger.info("🚀 Initializing Real-Time CFR Solver...")
        self.realtime_cfr_solver = RealTimeCFRSolver(use_gpu=True)
        self.logger.info("✅ Real-Time CFR Solver ready for live play!")

        self.table_data = {}
        self.player_data = []
        self.running = False
        self.last_html_content = None
        self.starting_stack = 6
        
        # Strategy utilization tracking
        self.strategy_stats = {
            'gpu_strategies_used': 0,
            'monte_carlo_fallbacks_used': 0,
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

        # Log the hand we're holding
        player_hole_cards = my_player.get('cards', [])
        community_cards = self.table_data.get('community_cards', [])
        
        if player_hole_cards:
            cards_str = ', '.join(player_hole_cards)
            self.logger.info(f"🃏 My Hand: {cards_str}")
            
            # Add basic hand description for better understanding
            if len(player_hole_cards) == 2:
                card1, card2 = player_hole_cards[0], player_hole_cards[1]
                # Extract ranks and suits - handle both single character and multi-character ranks
                if len(card1) >= 2:
                    if card1[-2:] in ['10']:  # Handle '10' specially
                        rank1, suit1 = '10', card1[-1]
                    else:
                        rank1, suit1 = card1[:-1], card1[-1]
                else:
                    rank1, suit1 = card1[0], card1[1] if len(card1) > 1 else ''
                
                if len(card2) >= 2:
                    if card2[-2:] in ['10']:  # Handle '10' specially
                        rank2, suit2 = '10', card2[-1]
                    else:
                        rank2, suit2 = card2[:-1], card2[-1]
                else:
                    rank2, suit2 = card2[0], card2[1] if len(card2) > 1 else ''
                
                # Normalize ranks (convert '10' to 'T' for comparison)
                def normalize_rank(rank):
                    return 'T' if rank == '10' else rank
                
                norm_rank1 = normalize_rank(rank1)
                norm_rank2 = normalize_rank(rank2)
                
                # Determine if suited or offsuit
                suited = "suited" if suit1 == suit2 else "offsuit"
                
                # Check for pocket pair
                if norm_rank1 == norm_rank2:
                    display_rank = rank1 if rank1 != '10' else 'T'
                    hand_desc = f"Pocket {display_rank}s"
                else:
                    # Sort ranks by strength for consistent description
                    rank_order = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
                    try:
                        if rank_order.index(norm_rank1) > rank_order.index(norm_rank2):
                            display_rank1 = rank1 if rank1 != '10' else 'T'
                            display_rank2 = rank2 if rank2 != '10' else 'T'
                            hand_desc = f"{display_rank1}{display_rank2} {suited}"
                        else:
                            display_rank1 = rank1 if rank1 != '10' else 'T'
                            display_rank2 = rank2 if rank2 != '10' else 'T'
                            hand_desc = f"{display_rank2}{display_rank1} {suited}"
                    except ValueError as e:
                        # Fallback if rank parsing fails
                        self.logger.warning(f"Could not parse card ranks '{rank1}', '{rank2}': {e}")
                        hand_desc = f"{card1} {card2} (raw)"
                
                self.logger.info(f"📝 Hand Type: {hand_desc}")
        else:
            self.logger.warning("⚠️  No hole cards detected!")
            
        if community_cards:
            community_str = ', '.join(community_cards)
            self.logger.info(f"🃏 Community Cards: {community_str}")

        # --- State Extraction for Hashing ---
        stage_map = {'preflop': 0, 'flop': 1, 'turn': 2, 'river': 3}
        stage_name = self.table_data.get('game_stage', 'preflop').lower()
        street = stage_map.get(stage_name, 0)
        
        # Log game stage after defining stage_name
        self.logger.info(f"📊 Game Stage: {stage_name.title()}")

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

        # 1. Try to get a strategy using exact match, then SAFE fuzzy matching if needed
        strategy, match_type = self.strategy_lookup.get_strategy_with_conservative_fallback(
            info_hash, state_components, player_hole_cards, community_cards)
        
        if strategy:
            if match_type == 'exact':
                self.logger.info(f"🎯 Using exact GPU-trained strategy for hash {info_hash}")
                self.strategy_stats['gpu_strategies_used'] += 1
            elif match_type == 'safe_fuzzy':
                self.logger.info(f"� Using SAFE fuzzy-matched GPU-trained strategy for hash {info_hash}")
                self.strategy_stats['gpu_strategies_used'] += 1
        else:
            # 2. If no match found (exact or fuzzy), run a fast Real-Time CFR solve for this spot
            self.logger.info(f"🔍 No precomputed strategy found for hash {info_hash}. Running FAST Real-Time CFR solve.")
            
            player_hole_cards = my_player.get('cards', [])
            if not player_hole_cards:
                self.logger.warning("Cannot decide action without hole cards.")
                return ACTION_FOLD, 0

            community_cards = self.table_data.get('community_cards', [])
            actions = my_player.get('available_actions', [ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE])
            num_opponents = sum(1 for p in self.player_data if not p.get('is_my_player', False) and not p.get('is_empty', False))

            # Use Real-Time CFR solver for high-quality live solving
            start_solve_time = time.time()
            try:
                # Determine quality level based on pot size and situation complexity
                if effective_pot > 5.0:  # Large pot = use detailed solving
                    quality_level = 'detailed'
                elif num_opponents > 3:  # Multiway = use detailed solving
                    quality_level = 'detailed'  
                elif stage_name in ['turn', 'river']:  # Later streets = normal+ solving
                    quality_level = 'normal'
                else:  # Standard situations
                    quality_level = 'normal'
                
                self.logger.info(f"🎯 Using CFR quality level: {quality_level} for pot=${effective_pot:.2f}")
                
                strategy = self.realtime_cfr_solver.solve_current_situation(
                    hole_cards=player_hole_cards,
                    community_cards=community_cards,
                    pot_size=effective_pot,
                    num_opponents=num_opponents,
                    position=0,  # Simplified for now
                    stage=stage_name,
                    quality_level=quality_level  # Use adaptive quality
                )
                solve_time = time.time() - start_solve_time
                self.logger.info(f"⚡ Real-Time CFR computed strategy in {solve_time:.2f}s: {strategy}")
                self.strategy_stats['cfr_fallbacks_used'] += 1
                
            except Exception as e:
                # Fallback to Monte Carlo if CFR fails
                self.logger.warning(f"Real-Time CFR failed ({e}), falling back to Monte Carlo")
                strategy = self.monte_carlo_solver.solve(player_hole_cards, community_cards, effective_pot, actions, stage_name, num_opponents, iterations=100)
                solve_time = time.time() - start_solve_time
                self.logger.info(f"🎲 Monte Carlo computed strategy in {solve_time:.2f}s: {strategy}")
                self.strategy_stats['monte_carlo_fallbacks_used'] += 1
        
        # Update total decisions and log stats periodically
        self.strategy_stats['total_decisions'] += 1
        if self.strategy_stats['total_decisions'] > 0 and self.strategy_stats['total_decisions'] % 10 == 0:
            gpu_usage_rate = (self.strategy_stats['gpu_strategies_used'] / self.strategy_stats['total_decisions']) * 100
            cfr_usage_rate = (self.strategy_stats['cfr_fallbacks_used'] / self.strategy_stats['total_decisions']) * 100
            mc_usage_rate = (self.strategy_stats['monte_carlo_fallbacks_used'] / self.strategy_stats['total_decisions']) * 100
            self.logger.info(f"📈 Strategy Usage: {gpu_usage_rate:.1f}% GPU-trained, {cfr_usage_rate:.1f}% Real-Time CFR, {mc_usage_rate:.1f}% Monte Carlo ({self.strategy_stats['total_decisions']} total decisions)")

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
        else:
            # Handle CFR solver format - convert action names to our constants
            cfr_action_map = {
                'fold': ACTION_FOLD,
                'check': ACTION_CHECK,
                'call': ACTION_CALL,
                'bet': ACTION_RAISE,
                'raise': ACTION_RAISE
            }
            # Convert CFR format to our action constants
            converted_strategy = {}
            for action_name, prob in strategy.items():
                mapped_action = cfr_action_map.get(action_name.lower(), action_name)
                if mapped_action in converted_strategy:
                    converted_strategy[mapped_action] += prob  # Combine probabilities for same action
                else:
                    converted_strategy[mapped_action] = prob
            strategy = converted_strategy

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

        # Create simplified strategy for action selection
        simple_strategy = {}
        
        # Handle precomputed strategy format (action_0, action_1, etc.)
        if 'action_0' in original_strategy:
            if 'action_0' in original_strategy:
                simple_strategy[ACTION_FOLD] = original_strategy['action_0']
            if 'action_1' in original_strategy:
                simple_strategy[ACTION_CALL] = original_strategy['action_1']
            if total_raise_prob > 0:
                simple_strategy[ACTION_RAISE] = total_raise_prob
        else:
            # Handle CFR solver format (fold, check, call, bet, raise)
            simple_strategy = strategy.copy()  # Use the converted strategy directly

        # Ensure CHECK is handled correctly if CALL is not available
        available_actions = my_player.get('available_actions', [])
        if ACTION_CHECK in available_actions and ACTION_CALL not in available_actions:
            if ACTION_CALL in simple_strategy:
                simple_strategy[ACTION_CHECK] = simple_strategy.pop(ACTION_CALL)
        
        # Also handle the reverse case
        if ACTION_CALL in available_actions and ACTION_CHECK not in available_actions:
            if ACTION_CHECK in simple_strategy:
                simple_strategy[ACTION_CALL] = simple_strategy.pop(ACTION_CHECK)

        # Filter strategy to only include available actions
        available_strategy = {a: p for a, p in simple_strategy.items() if a in available_actions}
        if not available_strategy:
            self.logger.error(f"No valid actions from strategy {simple_strategy} match available actions {available_actions}. Folding.")
            return ACTION_FOLD, 0

        # FIXED: Use probabilistic action selection instead of always picking max
        # This allows the bot to raise when the strategy suggests it, even if not the highest probability
        import random
        
        # Normalize probabilities to ensure they sum to 1.0
        total_prob = sum(available_strategy.values())
        if total_prob > 0:
            normalized_strategy = {a: p/total_prob for a, p in available_strategy.items()}
        else:
            # Fallback to equal probabilities
            normalized_strategy = {a: 1.0/len(available_strategy) for a in available_strategy}
        
        # Sample action based on probabilities
        rand_val = random.random()
        cumulative_prob = 0.0
        best_action = list(available_strategy.keys())[0]  # fallback
        
        for action, prob in normalized_strategy.items():
            cumulative_prob += prob
            if rand_val <= cumulative_prob:
                best_action = action
                break
        
        # Choose raise size based on individual action probabilities
        chosen_raise_size = "medium"  # default
        if best_action == ACTION_RAISE and raise_size_probs:
            chosen_raise_size = max(raise_size_probs.items(), key=lambda x: x[1])[0]
        
        self.logger.info(f"Bot decision: {best_action} (probabilistic selection from strategy: {available_strategy}, raise_size: {chosen_raise_size})")

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
        
        # --- TESTING FROM MULTIPLE FILES ---
        # Test different scenarios to verify decision-making
        test_files = [
            'examples/preflop_my_turn.html',
            'examples/flop_my_turn_check.html',
        ]
        
        for test_file in test_files:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"🎯 TESTING SCENARIO: {test_file}")
                logger.info(f"{'='*60}")
                bot.test_from_file(test_file)
            except Exception as e:
                logger.error(f"Error testing {test_file}: {e}")
                continue  # Continue with next test
        
        logger.info(f"\n{'='*60}")
        logger.info("🏁 ALL TESTS COMPLETED")
        logger.info(f"{'='*60}")
        
        # --- NORMAL EXECUTION ---
        # Uncomment the lines below to run in live mode
        if len(sys.argv) > 1 and sys.argv[1] == 'live':
            logger.info("🎮 STARTING LIVE MODE - Bot will capture HTML from screen!")
            if not bot.ui_controller.positions:
                logger.critical("UI positions not calibrated. Run the original poker_bot.py with 'calibrate' argument first.")
                sys.exit()
            bot.main_loop()
        else:
            logger.info("🧪 Running in test mode. Use 'python poker_bot_v2.py live' for live screen capture mode.")

    except Exception as e:
        logger.error(f"An error occurred in __main__: {e}", exc_info=True)
    finally:
        if bot:
            bot.close_logger()
        logger.info("PokerBotV2 application finished.")
