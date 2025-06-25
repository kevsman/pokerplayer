"""
train_cfr.py
This script is responsible for the offline training of the poker bot using Counterfactual Regret Minimization (CFR).
It simulates games where the bot plays against itself, learns from its regrets, and stores the resulting
strategies in a JSON file for the real-time bot to use.

Enhanced with GPU acceleration support for faster training.
"""
import random
import numpy as np
from collections import defaultdict
import sys
import logging

from hand_abstraction import HandAbstraction
from strategy_lookup import StrategyLookup
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator

# Try to import GPU acceleration modules
try:
    from gpu_accelerated_equity import GPUEquityCalculator
    from gpu_cfr_trainer import GPUCFRTrainer
    GPU_AVAILABLE = True
    print("GPU acceleration modules loaded successfully")
except ImportError as e:
    GPU_AVAILABLE = False
    print(f"GPU acceleration not available: {e}")

# Suppress DEBUG logs from hand_evaluator and all other modules unless WARNING or above
logging.basicConfig(level=logging.INFO)
logging.getLogger("hand_evaluator").setLevel(logging.WARNING)
logging.getLogger("hand_abstraction").setLevel(logging.WARNING)

sys.setrecursionlimit(2000) # Increased recursion limit for deep CFR trees
logger = logging.getLogger(__name__)
class CFRNode:
    def __init__(self, num_actions, actions):
        self.num_actions = num_actions
        self.actions = actions
        self.regret_sum = np.zeros(num_actions)
        self.strategy = np.zeros(num_actions)
        self.strategy_sum = np.zeros(num_actions)

    def get_strategy(self):
        """ Get current strategy from regret-matching."""
        positive_regrets = np.maximum(self.regret_sum, 0)
        normalizing_sum = np.sum(positive_regrets)
        if normalizing_sum > 0:
            self.strategy = positive_regrets / normalizing_sum
        else:
            self.strategy = np.full(self.num_actions, 1.0 / self.num_actions)
        return self.strategy

    def get_average_strategy(self):
        """ Get average strategy over all iterations."""
        normalizing_sum = np.sum(self.strategy_sum)
        if normalizing_sum > 0:
            return self.strategy_sum / normalizing_sum
        else:
            return np.full(self.num_actions, 1.0 / self.num_actions)

class CFRTrainer:
    def __init__(self, num_players=6, big_blind=2, small_blind=1, use_gpu=True):
        self.num_players = num_players
        self.bb = big_blind
        self.sb = small_blind
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
        self.hand_evaluator = HandEvaluator()
        
        # Use GPU-accelerated equity calculator if available
        if self.use_gpu:
            logger.info("Initializing CFR trainer with GPU acceleration")
            self.equity_calculator = GPUEquityCalculator(use_gpu=True)
            # Also initialize GPU CFR trainer for batch operations
            self.gpu_trainer = GPUCFRTrainer(num_players, big_blind, small_blind, use_gpu=True)
        else:
            logger.info("Initializing CFR trainer with CPU processing")
            self.equity_calculator = EquityCalculator()
            self.gpu_trainer = None
        
        # Always use CPU equity calculator for hand abstraction (more compatible)
        self.cpu_equity_calculator = EquityCalculator()
        self.abstraction = HandAbstraction(self.hand_evaluator, self.cpu_equity_calculator)
        self.strategy_lookup = StrategyLookup()
        self.nodes = {}
        # Add a cache for hand evaluation at showdown
        self._showdown_eval_cache = {}
        # Add cycle detection to prevent infinite recursion
        self._recursion_states = set()

    def get_node(self, info_set, actions):
        if info_set not in self.nodes:
            self.nodes[info_set] = CFRNode(len(actions), actions)
        return self.nodes[info_set]

    def get_available_actions(self, current_bet, player_bet, history):
        actions = ['fold']
        if current_bet == player_bet:
            actions.append('check')
        else:
            actions.append('call')
        
        # Limit raises to 2 per round for training (bet, raise, reraise only)
        num_raises = history.split('|')[-1].count('r')
        if num_raises < 2:  # Reduced from 4 to 2
            actions.append('raise')
        return actions

    def is_round_complete(self, history, active_mask, bets, street):
        """
        Determine if the current betting round is complete and should advance to next street.
        
        Rules:
        1. If only one player is active, round is complete
        2. All active players must have equal bets
        3. All active players must have had a chance to act (or we're at start of round with all checks)
        """
        active_players = [i for i in range(len(active_mask)) if active_mask[i]]
        
        # Rule 1: Only one active player
        if len(active_players) <= 1:
            return True
        
        # Rule 2: All active players must have equal bets
        active_bets = [bets[i] for i in active_players]
        if len(set(active_bets)) != 1:
            return False
        
        # Rule 3: Check if sufficient action has occurred
        current_round_actions = history.split('|')[-1] if '|' in history else history
        
        # Count non-fold actions in this round
        action_count = len([a for a in current_round_actions if a in 'xrcb'])
        
        # Special case: if no actions yet and we're at the start, not complete
        if action_count == 0:
            return False
        
        # If all bets are 0, need at least (active_players) checks to complete
        max_bet = max(active_bets) if active_bets else 0
        if max_bet == 0:
            check_count = current_round_actions.count('x')
            is_complete = check_count >= len(active_players)
            return is_complete
        else:
            # There was betting/raising, need enough actions to give everyone a chance
            is_complete = action_count >= len(active_players)
            return is_complete

    def cfr(self, cards, history, pot, bets, active_mask, street, current_player, reach_probabilities, depth=0):
        # Create a normalized state identifier for better cycle detection
        # Normalize bets relative to the minimum bet to catch equivalent states
        min_bet = min(bets) if len(bets) > 0 else 0
        normalized_bets = tuple(b - min_bet for b in bets)
        state_id = (history, normalized_bets, tuple(active_mask), street, current_player)
        
        # Check for cycles with a sliding window approach
        if len(self._recursion_states) > 0:
            # Check if we've seen this exact state recently
            if state_id in self._recursion_states:
                logger.warning(f"Cycle detected at depth {depth}, history={history[-20:]}, returning zero payoffs")
                return np.zeros(self.num_players)
        
        # Keep only recent states to prevent memory buildup
        if len(self._recursion_states) > 100:
            # Keep only the most recent states
            self._recursion_states = set(list(self._recursion_states)[-50:])
        
        # Add current state to recursion tracking
        self._recursion_states.add(state_id)
        
        try:
            # ULTRA aggressive termination for training
            if depth > 10:  # Reduced from 15
                return np.zeros(self.num_players)
            
            # Also terminate if the game gets too complex (too many actions)
            if len(history) > 20:  # If history string is too long
                print(f"DEBUG: GAME TOO COMPLEX (history length {len(history)}), returning zeros")
                logger.warning(f"CFR game too complex at depth {depth}, history length {len(history)}, terminating early")
                return np.zeros(self.num_players)
            
            # Terminal state: only one player left
            if sum(active_mask) == 1:
                winner_index = np.where(active_mask)[0][0]
                payoffs = np.zeros(self.num_players)
                payoffs[winner_index] = pot
                return payoffs

            # Terminal state: showdown after the river
            if street > 3: # 0:preflop, 1:flop, 2:turn, 3:river
                payoffs = np.zeros(self.num_players)
                community_cards = cards[self.num_players*2 : self.num_players*2 + 5]
                
                active_player_indices = np.where(active_mask)[0]
                player_hands = {i: cards[i*2:i*2+2] for i in active_player_indices}
                # Use cache for hand evaluation
                evals = {}
                for i, h in player_hands.items():
                    # Use tuple for hashable key
                    key = (tuple(sorted(h)), tuple(sorted(community_cards)))
                    if key in self._showdown_eval_cache:
                        evals[i] = self._showdown_eval_cache[key]
                    else:
                        evals[i] = self.hand_evaluator.evaluate_hand(h, community_cards)
                        self._showdown_eval_cache[key] = evals[i]
                
                best_rank_value = -1
                for i in active_player_indices:
                    if evals[i]['rank_value'] > best_rank_value:
                        best_rank_value = evals[i]['rank_value']

                winners = [i for i in active_player_indices if evals[i]['rank_value'] == best_rank_value]
                
                for winner_idx in winners:
                    payoffs[winner_idx] = pot / len(winners)
                return payoffs

            # Start of a new betting round if history indicates it
            if history.endswith('|'):
                # A new betting round begins. Find the first player to act.
                # Post-flop, action starts from the Small Blind (player 1).
                player_to_act = 1
                while not active_mask[player_to_act]:
                    player_to_act = (player_to_act + 1) % self.num_players
                current_player = player_to_act

            # --- Main recursive step ---
            # Find next active player
            next_player = (current_player + 1) % self.num_players
            while not active_mask[next_player]:
                next_player = (next_player + 1) % self.num_players

            # Get info set
            community = []
            if street > 0:
                community = cards[self.num_players*2 : self.num_players*2 + 3 + (street - 1)]
            
            hand_bucket = self.abstraction.bucket_hand(cards[current_player*2:current_player*2+2], community, street, sum(active_mask)-1)
            board_bucket = self.abstraction.bucket_board(community, street)
            info_set = f"{street}|{hand_bucket}|{board_bucket}|{history}"

            actions = self.get_available_actions(max(bets), bets[current_player], history)
            node = self.get_node(info_set, actions)
            strategy = node.get_strategy()

            action_utils = np.zeros((self.num_players, len(actions)))

            for i, action in enumerate(actions):
                next_reach = reach_probabilities.copy()
                next_reach[current_player] *= strategy[i]
                
                history_char = action[0]
                if action == 'check':
                    history_char = 'x' # Use 'x' for check to distinguish from 'c' for call
                
                new_history = history + history_char
                new_bets = bets.copy()
                new_pot = pot
                new_active_mask = active_mask.copy()

                if action == 'fold':
                    new_active_mask[current_player] = False
                    action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach, depth+1)
                
                elif action == 'call':
                    amount_to_call = max(bets) - new_bets[current_player]
                    new_bets[current_player] += amount_to_call
                    new_pot += amount_to_call
                    
                    # Check if betting round is complete after this call
                    if self.is_round_complete(new_history, new_active_mask, new_bets, street):
                        # Advance to next street
                        action_utils[:, i] = self.cfr(cards, new_history + '|', new_pot, new_bets, new_active_mask, street + 1, 0, next_reach, depth+1)
                    else:
                        # Continue in current round
                        action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach, depth+1)

                elif action == 'check':
                    # Check if betting round is complete after this check
                    if self.is_round_complete(new_history, new_active_mask, new_bets, street):
                        # Advance to next street
                        action_utils[:, i] = self.cfr(cards, new_history + '|', new_pot, new_bets, new_active_mask, street + 1, 0, next_reach, depth+1)
                    else:
                        # Continue in current round
                        action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach, depth+1)

                elif action == 'raise':
                    # No-limit raise logic: minimum raise is the size of the previous bet or BB, maximum is all-in (for training, use pot as a soft cap)
                    call_amount = max(bets) - new_bets[current_player]
                    min_raise = max(self.bb, call_amount)
                    # For CFR, we can use a reasonable abstraction: allow min_raise and pot-sized raise
                    # To avoid exponential growth, cap the raise to the current pot size
                    max_raise = new_pot  # Pot-sized raise as a soft cap
                    raise_amount = min_raise  # Use min_raise for simplicity, but could randomize or add more sizes for abstraction
                    amount_to_add = call_amount + raise_amount
                    new_bets[current_player] += amount_to_add
                    new_pot += amount_to_add
                    action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach, depth+1)

            # Calculate node values and update regrets
            node_util_for_player = np.sum(strategy * action_utils[current_player])
            regret = action_utils[current_player] - node_util_for_player
            
            reach_prob = reach_probabilities[current_player]
            cfr_reach = np.prod(np.delete(reach_probabilities, current_player))

            node.regret_sum += cfr_reach * regret
            node.strategy_sum += reach_prob * strategy

            return np.dot(action_utils, strategy)
            
        finally:
            # Remove current state from recursion tracking when we're done with this call
            self._recursion_states.discard(state_id)


    def train(self, iterations):
        import traceback
        logger.info(f"Starting CFR training with {iterations} iterations")

        for i in range(iterations):
            # Reset cycle detection for each iteration
            self._recursion_states.clear()
            
            if i > 0 and i % 100 == 0:
                logger.info(f"Iteration {i}/{iterations}")
            
            # Generate standard deck - compatible with both GPU and CPU calculators
            suits = ['h', 'd', 'c', 's']
            ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
            deck = [rank + suit for rank in ranks for suit in suits]
            random.shuffle(deck)
            pot = self.sb + self.bb
            bets = np.zeros(self.num_players)
            bets[1] = self.sb # Player 1 is SB
            bets[2] = self.bb # Player 2 is BB (UTG is player 3)
            active_mask = np.ones(self.num_players, dtype=bool)
            reach_probabilities = np.ones(self.num_players)
            try:
                self.cfr(cards=deck, history="", pot=pot, bets=bets, active_mask=active_mask, street=0, current_player=3 % self.num_players, reach_probabilities=reach_probabilities)
            except Exception as e:
                logger.error(f"Exception in iteration {i+1}: {e}")
                logger.error(traceback.format_exc())
                break
        
        logger.info(f"Training complete. Converting {len(self.nodes)} nodes to strategy format...")
        return self._finalize_strategies()
        for info_set, node in self.nodes.items():
            try:
                street, hand_bucket, board_bucket, history_str = info_set.split('|', 3)
                actions = node.actions
                avg_strategy = node.get_average_strategy()
                strategy_dict = {act: p for act, p in zip(actions, avg_strategy)}
                self.strategy_lookup.add_strategy(street, hand_bucket, board_bucket, list(strategy_dict.keys()), strategy_dict)
                strategy_count += 1
            except ValueError as e:
                logger.warning(f"Could not parse info_set: {info_set}, error: {e}")
                continue
        
        logger.info(f"Converted {strategy_count} strategies. Saving to file...")
        self.strategy_lookup.save_strategies()
        logger.info("CFR training completed successfully")

    def train_with_gpu_acceleration(self, iterations, batch_size=50):
        """
        Enhanced training method that uses GPU acceleration when available.
        Processes multiple scenarios in parallel for faster training.
        """
        if not self.use_gpu or not self.gpu_trainer:
            logger.warning("GPU acceleration not available, falling back to standard training")
            return self.train(iterations)
        
        logger.info(f"Starting GPU-accelerated CFR training with {iterations} iterations, batch size {batch_size}")
        
        # Use the GPU trainer's batch processing capabilities
        try:
            # Create batches of training scenarios
            for batch_start in range(0, iterations, batch_size):
                current_batch_size = min(batch_size, iterations - batch_start)
                logger.info(f"Processing batch {batch_start // batch_size + 1}, iterations {batch_start}-{batch_start + current_batch_size}")
                
                # Reset cycle detection for each batch
                self._recursion_states.clear()
                
                # Generate batch of initial game states
                batch_scenarios = []
                for _ in range(current_batch_size):
                    # Generate standard deck - compatible with both GPU and CPU calculators
                    suits = ['h', 'd', 'c', 's']
                    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
                    deck = [rank + suit for rank in ranks for suit in suits]
                    random.shuffle(deck)
                    pot = self.sb + self.bb
                    bets = np.zeros(self.num_players)
                    bets[1] = self.sb  # Player 1 is SB
                    bets[2] = self.bb  # Player 2 is BB
                    active_mask = np.ones(self.num_players, dtype=bool)
                    reach_probabilities = np.ones(self.num_players)
                    
                    scenario = {
                        'cards': deck,
                        'history': "",
                        'pot': pot,
                        'bets': bets,
                        'active_mask': active_mask,
                        'street': 0,
                        'current_player': 3 % self.num_players,
                        'reach_probabilities': reach_probabilities
                    }
                    batch_scenarios.append(scenario)
                
                # Process batch using GPU trainer if it has batch capabilities
                if hasattr(self.gpu_trainer, 'process_batch_scenarios'):
                    self.gpu_trainer.process_batch_scenarios(batch_scenarios, self.nodes)
                else:
                    # Fallback to individual processing with GPU equity calculations
                    for scenario in batch_scenarios:
                        try:
                            self.cfr(
                                cards=scenario['cards'],
                                history=scenario['history'],
                                pot=scenario['pot'],
                                bets=scenario['bets'],
                                active_mask=scenario['active_mask'],
                                street=scenario['street'],
                                current_player=scenario['current_player'],
                                reach_probabilities=scenario['reach_probabilities']
                            )
                        except Exception as e:
                            logger.error(f"Exception in GPU-accelerated CFR iteration: {e}")
                            continue
        
        except Exception as e:
            logger.error(f"Error in GPU-accelerated training: {e}")
            logger.warning("Falling back to standard CPU training")
            return self.train(iterations)
        
        logger.info(f"GPU-accelerated training complete. Converting {len(self.nodes)} nodes to strategy format...")
        return self._finalize_strategies()
    
    def _finalize_strategies(self):
        """Convert trained nodes to strategy format and save."""
        strategy_count = 0
        for info_set, node in self.nodes.items():
            avg_strategy = node.get_average_strategy()
            if np.sum(avg_strategy) > 0:  # Only save non-zero strategies
                actions = node.actions
                strategy_dict = {action: float(prob) for action, prob in zip(actions, avg_strategy)}
                self.strategy_lookup.save_strategy(info_set, strategy_dict)
                strategy_count += 1
        
        logger.info(f"Saved {strategy_count} strategies to lookup table")
        return strategy_count

    # ...existing code...
if __name__ == "__main__":
    trainer = CFRTrainer(num_players=6)  # 6 players for realistic training
    trainer.train(iterations=50000)  # Start with smaller number for testing
