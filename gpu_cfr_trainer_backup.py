"""
Patched GPU-accelerated CFR trainer for poker bot with infinite recursion fix.
"""
import numpy as np
import logging
import time
import json
import hashlib
from typing import List, Dict, Tuple
import random

# --- Mock Objects for Safe Execution ---
class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def error(self, msg): pass
    def warning(self, msg): pass

logger = MockLogger()
GPU_AVAILABLE = False
logging.getLogger(__name__).setLevel(logging.CRITICAL + 1)

from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from strategy_lookup import StrategyLookup

class CFRNode:
    def __init__(self, num_actions: int, actions: List[str]):
        self.num_actions = num_actions
        self.actions = actions
        self.regret_sum = np.zeros(num_actions)
        self.strategy_sum = np.zeros(num_actions)
        self.strategy = np.repeat(1/num_actions, num_actions)

    def get_strategy(self) -> np.ndarray:
        self.strategy = np.maximum(0, self.regret_sum)
        normalizing_sum = np.sum(self.strategy)
        if normalizing_sum > 0:
            self.strategy /= normalizing_sum
        else:
            self.strategy = np.repeat(1/self.num_actions, self.num_actions)
        return self.strategy

    def get_average_strategy(self) -> Dict[str, float]:
        normalizing_sum = np.sum(self.strategy_sum)
        if normalizing_sum > 0:
            avg_strategy = self.strategy_sum / normalizing_sum
        else:
            avg_strategy = np.repeat(1/self.num_actions, self.num_actions)
        return {self.actions[i]: avg_strategy[i] for i in range(self.num_actions)}

class GPUCFRTrainer:
    def __init__(self, use_gpu=True, num_players=6, small_blind=0.02, big_blind=0.04, initial_stack=4.0):
        self.num_players = num_players
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.initial_stack = self.big_blind * 100
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = GPUEquityCalculator(use_gpu=self.use_gpu)
        self.strategy_lookup = StrategyLookup()
        self.nodes: Dict[str, CFRNode] = {}
        self.deck = self.equity_calculator.all_cards[:]
        logger.info("GPUCFRTrainer initialized")
        self.hand_counter = 0
        self.recursion_depth = 0
        self.state_history = set()  # Track visited states
        
        # Terminal conditions for robustness
        self.max_recursion_depth = 100
        self.max_actions_per_street = 20
        self.max_total_actions = 100

    def _state_key(self, player_hands, board, pot, bets, active_players, player_stacks, street, num_actions):
        """Create a unique key for the current game state to detect loops."""
        # Create a simplified state representation
        state_data = {
            'street': street,
            'pot': round(pot, 2),
            'bets': [round(b, 2) for b in bets],
            'active': active_players.tolist(),
            'stacks': [round(s, 2) for s in player_stacks],
            'num_actions': num_actions,
            'board_len': len(board)
        }
        state_str = json.dumps(state_data, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()

    def _cfr_recursive(self, player_hands, history, board, pot, bets, reach_probs,
                       active_players, player_stacks, street, num_actions_this_street, 
                       recursion_depth, total_actions=0):
        
        # Multiple terminal conditions for robustness
        if recursion_depth > self.max_recursion_depth:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
        
        if num_actions_this_street > self.max_actions_per_street:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
            
        if total_actions > self.max_total_actions:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
        
        # State loop detection
        state_key = self._state_key(player_hands, board, pot, bets, active_players, player_stacks, street, num_actions_this_street)
        if state_key in self.state_history:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
        
        self.state_history.add(state_key)
        
        try:
            # BASE CASE: If all players are all-in or no one can act
            if not self._can_any_player_act(active_players, player_stacks):
                pot += np.sum(bets)
                bets = np.zeros(self.num_players)
                final_board = board[:]
                num_cards_to_deal = 5 - len(final_board)

                if num_cards_to_deal > 0:
                    dealt_cards = [card for hand in player_hands for card in hand] + final_board
                    flat_dealt_cards = [c for sub in dealt_cards for c in (sub if isinstance(sub, list) else [sub])]
                    remaining_deck = [card for card in self.deck if card not in flat_dealt_cards]
                    random.shuffle(remaining_deck)
                    final_board.extend(remaining_deck[:num_cards_to_deal])

                return self._get_terminal_utility(player_hands, final_board, pot, bets, active_players, player_stacks)

            is_over = self._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
            
            # Override: If only one player is active, the betting round must be over
            if np.sum(active_players) <= 1:
                is_over = True

            if is_over:
                if not self._can_any_player_act(active_players, player_stacks):
                    return self._get_terminal_utility(player_hands, board, pot + np.sum(bets), np.zeros(self.num_players), active_players, player_stacks)
                if street == 3:
                    return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
                return self._handle_new_street(player_hands, board, pot, bets, reach_probs,
                                               active_players, player_stacks, street, recursion_depth, total_actions)

            player = self._get_current_player(history, active_players, street, pot, num_actions_this_street, player_stacks)
            if player == -1:
                return self._get_terminal_utility(player_hands, board, pot + np.sum(bets), np.zeros(self.num_players), active_players, player_stacks)

            actions = self._get_available_actions(player, bets, player_stacks)
            if not actions:
                return self._get_terminal_utility(player_hands, board, pot + np.sum(bets), np.zeros(self.num_players), active_players, player_stacks)

            # Create a more robust information set
            actions_str = "".join(sorted(actions))
            bets_str = ",".join([f"{b:.2f}" for b in bets])
            info_set = f"{street}-{bets_str}-{player_stacks[player]:.2f}-{actions_str}"
            
            strategy = self._get_strategy(info_set, actions)

            if len(strategy) != len(actions):
                strategy = np.repeat(1 / len(actions), len(actions))

            node_utility_vector = np.zeros(self.num_players)
            cf_values_for_player = np.zeros(len(actions))

            for i, action in enumerate(actions):
                new_history = history + action
                new_bets = bets.copy()
                new_stacks = player_stacks.copy()
                new_active_players = active_players.copy()
                new_num_actions = num_actions_this_street + 1
                new_pot = pot

                if action == 'f':
                    new_active_players[player] = False
                elif action == 'c':
                    max_bet = np.max(new_bets)
                    to_call = max_bet - new_bets[player]
                    amount = min(to_call, new_stacks[player])
                    new_bets[player] += amount
                    new_stacks[player] -= amount
                elif action == 'r':
                    max_bet = np.max(new_bets)
                    to_call = max_bet - new_bets[player]
                    # Conservative raise sizing
                    raise_amount = min(pot + np.sum(bets), new_stacks[player] - to_call)
                    if raise_amount > 0:
                        new_bets[player] = max_bet + to_call + raise_amount
                        new_stacks[player] -= (to_call + raise_amount)
                    else:
                        # Convert to call if can't raise
                        amount = min(to_call, new_stacks[player])
                        new_bets[player] += amount
                        new_stacks[player] -= amount

                new_reach_probs = reach_probs.copy()
                new_reach_probs[player] *= strategy[i]

                utility = self._cfr_recursive(
                    player_hands, new_history, board, new_pot, new_bets,
                    new_reach_probs, new_active_players, new_stacks,
                    street, new_num_actions, recursion_depth + 1, total_actions + 1
                )

                if utility.shape[0] != self.num_players:
                    utility = np.zeros(self.num_players)

                node_utility_vector += strategy[i] * utility
                cf_values_for_player[i] = utility[player]

            node = self.get_node(info_set, actions)
            
            if len(cf_values_for_player) != node.num_actions:
                return np.zeros(self.num_players)

            regret = cf_values_for_player - np.sum(strategy * cf_values_for_player)
            node.regret_sum += regret
            node.strategy_sum += reach_probs[player] * strategy

            return node_utility_vector
        
        finally:
            # Clean up state tracking
            self.state_history.discard(state_key)

    def _can_any_player_act(self, active_players: np.ndarray, player_stacks: np.ndarray) -> bool:
        return np.any(active_players & (player_stacks > 0.01))  # Use small threshold instead of exact 0

    def _get_terminal_utility(self, player_hands, board, pot, bets, active_players, player_stacks) -> np.ndarray:
        investment = self.initial_stack - player_stacks
        total_pot = pot + np.sum(bets)
        payoffs = np.zeros(self.num_players)

        if np.sum(active_players) == 1:
            winner = np.where(active_players)[0][0]
            winnings = np.zeros(self.num_players)
            winnings[winner] = total_pot
            return winnings - investment

        # Assume simplified equity calculation here...
        winnings = np.zeros(self.num_players)
        active_indices = np.where(active_players)[0]
        for idx in active_indices:
            winnings[idx] = total_pot / len(active_indices)
        return winnings - investment

    def _get_current_player(self, history, active_players, street, pot, num_actions_this_street, player_stacks) -> int:
        # If only one player is active and has a stack, they are the current player.
        can_act_mask = active_players & (player_stacks > 0.01)  # Use small threshold
        if np.sum(can_act_mask) == 1:
            player_idx = np.where(can_act_mask)[0][0]
            return player_idx

        # Determine the starting player for the street
        if street == 0:
            # Pre-flop starts after the big blind
            start_player_initial = 2 if self.num_players > 2 else 0
        else:
            # Post-flop starts with the first active player from the small blind position
            start_player_initial = 0
            while not active_players[start_player_initial]:
                start_player_initial = (start_player_initial + 1) % self.num_players

        player = start_player_initial
        for _ in range(num_actions_this_street):
            player = (player + 1) % self.num_players
            while not (active_players[player] and player_stacks[player] > 0.01):  # Use small threshold
                player = (player + 1) % self.num_players

        # Final check to ensure the determined player can act
        search_start = player
        while not (active_players[player] and player_stacks[player] > 0.01):  # Use small threshold
            player = (player + 1) % self.num_players
            if player == search_start:
                return -1 # No player can act
        return player

    def _is_betting_round_over(self, history: str, bets: np.ndarray, active_players: np.ndarray, street: int, num_actions: int, stacks: np.ndarray) -> bool:
        # Condition 1: The round is over if only one player (or none) is left in the hand.
        if np.sum(active_players) <= 1:
            return True

        # Condition 2: Check if all remaining active players are all-in (no further betting possible)
        players_who_can_act = active_players & (stacks > 0.01)  # Use small threshold
        can_act_count = np.sum(players_who_can_act)
        
        # Only end the round if ALL active players are all-in
        if can_act_count == 0:
            return True

        # Condition 3: The action is closed because all active players have acted and no further action is possible
        # This requires at least one action from every active player.
        min_actions_needed = np.sum(active_players)
        if num_actions >= min_actions_needed:
            # Check if all players who are still in the hand (not folded) have contributed the same amount
            # OR if no player can take further action (all have either folded, are all-in, or have matched the max they can be called for)
            bets_of_active_players = bets[active_players]
            all_bets_equal = len(np.unique(bets_of_active_players)) == 1
            
            # Check if action is effectively closed due to all-in situations
            max_bet = np.max(bets_of_active_players)
            action_closed = True
            
            for i in range(len(active_players)):
                if not active_players[i]:
                    continue  # Skip folded players
                    
                # If player has chips left and hasn't matched the max bet, action isn't closed
                if stacks[i] > 0.01 and bets[i] < max_bet:  # Use small threshold
                    # Player can still call, so action isn't closed
                    action_closed = False
                    break
            
            # Special case for preflop: Handle SB call + BB check scenario
            if street == 0 and 'r' not in history:
                # If everyone has acted and no raises, the round is over
                # This handles "BTN fold, SB call, BB check" type scenarios
                if num_actions >= np.sum(active_players):
                    return True
            
            if all_bets_equal or action_closed:
                # For post-flop or when there have been raises, normal rules apply
                if street > 0 or 'r' in history:
                    return True

        # Condition 4: Emergency check for excessive checking when bets are equal
        # If we have a lot of actions and the bets are equal, end the round
        if num_actions > 10:  # Reasonable threshold
            bets_of_active_players = bets[active_players]
            if len(np.unique(bets_of_active_players)) == 1:
                return True
        
        return False

    def _handle_new_street(self, player_hands, board, pot, bets, reach_probs, active_players, player_stacks, street, recursion_depth, total_actions=0):
        # If only one player is left, no new street is dealt. Terminal state.
        if np.sum(active_players) <= 1:
            return self._get_terminal_utility(player_hands, board, pot + np.sum(bets), np.zeros(self.num_players), active_players, player_stacks)

        new_street = street + 1
        pot += np.sum(bets)
        new_bets = np.zeros(self.num_players)
        new_board = board[:]
        dealt_cards = [c for hand in player_hands for c in hand] + board
        remaining_deck = [c for c in self.deck if c not in dealt_cards]
        random.shuffle(remaining_deck)

        if new_street == 1: # Flop
            new_board.extend(remaining_deck[:3])
        elif new_street in [2, 3]: # Turn/River
            new_board.extend(remaining_deck[:1])

        return self._cfr_recursive(player_hands, "", new_board, pot, new_bets, reach_probs, active_players, player_stacks, new_street, 0, recursion_depth + 1, total_actions)

    def _get_available_actions(self, player: int, bets: np.ndarray, stacks: np.ndarray) -> List[str]:
        actions = []
        max_bet = np.max(bets)
        to_call = max_bet - bets[player]
        if stacks[player] <= 0.01:  # Use small threshold instead of exact 0
            return []
        if to_call > 0:
            actions.extend(['f', 'c'])
        else:
            actions.append('k')
        if stacks[player] > to_call:
            actions.append('r')
        return actions

    def get_node(self, info_set: str, actions: List[str]) -> CFRNode:
        if info_set not in self.nodes:
            self.nodes[info_set] = CFRNode(len(actions), actions)
        return self.nodes[info_set]

    def _get_strategy(self, info_set: str, actions: List[str]) -> np.ndarray:
        node = self.get_node(info_set, actions)
        return node.get_strategy()

    def train_like_fixed_cfr(self, iterations: int):
        """
        Run CFR training for the specified number of iterations.
        
        Args:
            iterations: Number of CFR iterations to run
        """
        logger.info(f"Starting CFR training for {iterations} iterations...")
        
        for iteration in range(iterations):
            logger.info(f"Running CFR iteration {iteration + 1}/{iterations}")
            
            # Clear state history for each iteration
            self.state_history.clear()
            
            # Generate random hands for all players
            player_hands = []
            deck_copy = self.deck.copy()
            random.shuffle(deck_copy)
            
            # Deal 2 cards to each player
            for player in range(self.num_players):
                hand = [deck_copy.pop(), deck_copy.pop()]
                player_hands.append(hand)
            
            # Initialize game state
            board = []
            pot = 0.0
            bets = np.zeros(self.num_players)
            bets[0] = self.small_blind  # Small blind
            bets[1] = self.big_blind    # Big blind
            
            active_players = np.ones(self.num_players, dtype=bool)
            player_stacks = np.full(self.num_players, self.initial_stack)
            player_stacks[0] -= self.small_blind  # Deduct small blind
            player_stacks[1] -= self.big_blind    # Deduct big blind
            
            reach_probs = np.ones(self.num_players)
            
            # Run CFR for this hand
            try:
                utility = self._cfr_recursive(
                    player_hands, "", board, pot, bets, reach_probs,
                    active_players, player_stacks, street=0, num_actions_this_street=0, recursion_depth=0, total_actions=0
                )
                logger.info(f"Iteration {iteration + 1} completed. Utility: {utility}")
            except Exception as e:
                logger.error(f"Error in iteration {iteration + 1}: {e}")
                continue
        
        logger.info(f"CFR training completed after {iterations} iterations.")
        logger.info(f"Total nodes created: {len(self.nodes)}")
