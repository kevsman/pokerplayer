"""
Robust GPU-accelerated CFR trainer for poker bot with infinite recursion fix.
"""
import numpy as np
import logging
import time
import json
import hashlib
from typing import List, Dict, Tuple
import random

# --- GPU Detection ---
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("GPU acceleration available in GPUCFRTrainer")
except ImportError:
    GPU_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("GPU not available in GPUCFRTrainer, falling back to CPU")

from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from gpu_strategy_manager import GPUStrategyManager # Import the new manager

class GPUCFRTrainer:
    def __init__(self, num_players: int = 6, small_blind: float = 0.02, big_blind: float = 0.04, use_gpu: bool = True, initial_stack: float = 4.0):
        self.num_players = num_players
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.initial_stack = self.big_blind * 100
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = GPUEquityCalculator(use_gpu=self.use_gpu)
        self.strategy_manager = GPUStrategyManager() # Use the new manager
        self.deck = self.equity_calculator.all_cards[:]
        self.hand_counter = 0
        self.recursion_depth = 0
        
        # Terminal conditions
        self.max_recursion_depth = 100
        self.max_actions_per_street = 25
        self.max_total_actions = 100

    def train(self, iterations: int, batch_size: int = 1024):
        """Main training loop for vectorized GPU-accelerated CFR."""
        if not self.use_gpu:
            logger.error("GPU is not available. Vectorized training requires a GPU.")
            return

        logger.info(f"Starting vectorized training for {iterations} iterations with batch size {batch_size}.")

        for i in range(iterations):
            start_time = time.time()
            
            game_states = self._sample_initial_states_gpu(batch_size)
            
            self._cfr_vectorized_iteration(game_states)

            end_time = time.time()
            logger.info(f"Iteration {i+1}/{iterations} completed in {end_time - start_time:.2f}s")

            if (i + 1) % 100 == 0: # Save less frequently
                self.strategy_manager.save_strategy_table()
                logger.info(f"Strategy table saved at iteration {i+1}")

        self.strategy_manager.save_strategy_table()
        logger.info("Final strategy table saved.")

    def _sample_initial_states_gpu(self, batch_size: int) -> Dict:
        """Sample a batch of initial game states for training, directly on the GPU."""
        hands, boards = self.equity_calculator.deal_hands_and_boards_vectorized(
            num_players=self.num_players, num_games=batch_size
        )

        return {
            "pot": cp.full(batch_size, self.small_blind + self.big_blind, dtype=cp.float32),
            "bets": cp.tile(cp.array([self.small_blind, self.big_blind] + [0] * (self.num_players - 2), dtype=cp.float32), (batch_size, 1)),
            "active_players": cp.ones((batch_size, self.num_players), dtype=cp.bool_),
            "player_stacks": cp.full((batch_size, self.num_players), self.initial_stack, dtype=cp.float32),
            "reach_probs": cp.ones((batch_size, self.num_players), dtype=cp.float32),
            "current_player": cp.zeros(batch_size, dtype=cp.int32),
            "last_aggressor": cp.full(batch_size, 1, dtype=cp.int32),
            "has_acted_this_round": cp.zeros((batch_size, self.num_players), dtype=cp.bool_),
            "history_count": cp.zeros(batch_size, dtype=cp.int32),
            "max_history": 100,
            "history_indices": cp.zeros((batch_size, 100), dtype=cp.int32),
            "history_actions": cp.zeros((batch_size, 100), dtype=cp.int32),
            "history_strategies": cp.zeros((batch_size, 100, 3), dtype=cp.float32),
            "hands": hands,
            "board": boards
        }

    def _cfr_vectorized_iteration(self, game_states: Dict):
        """
        Performs one iteration of vectorized CFR by processing a batch of game states through each street.
        """
        # Pre-flop, Flop, Turn, River
        for street in range(4):
            game_states = self._process_street_vectorized(game_states, street=street)
        
        final_utilities = self._calculate_showdown_utilities(game_states)
        self._update_regrets_and_strategy(game_states, final_utilities)

    def _process_street_vectorized(self, game_states: Dict, street: int) -> Dict:
        """
        Processes a full betting round for a batch of game states on the GPU.
        """
        batch_size = game_states['pot'].shape[0]

        if street > 0:
            active_for_street_mask = cp.sum(game_states['active_players'], axis=1) > 1
            if cp.any(active_for_street_mask):
                reset_indices = cp.where(active_for_street_mask)[0]
                game_states['bets'][reset_indices] = 0
                game_states['has_acted_this_round'][reset_indices] = False
                game_states['last_aggressor'][reset_indices] = -1
                active_players_to_reset = game_states['active_players'][reset_indices]
                first_to_act = cp.argmax(active_players_to_reset, axis=1).astype(cp.int32)
                game_states['current_player'][reset_indices] = first_to_act

        betting_open = cp.ones(batch_size, dtype=cp.bool_)
        betting_open[cp.sum(game_states['active_players'], axis=1) <= 1] = False

        for action_count in range(self.max_actions_per_street):
            if not cp.any(betting_open):
                break

            active_game_states = self._get_active_games(game_states, betting_open)
            
            # Use hashing for info state keys
            info_state_hashes = self._get_info_state_hashes(active_game_states, street)
            
            node_indices = self.strategy_manager.get_node_indices(info_state_hashes)
            strategies = self.strategy_manager.get_strategies(node_indices)
            
            action_indices = self._sample_actions_vectorized(strategies)

            self._record_history_vectorized(game_states, node_indices, action_indices, strategies, betting_open)

            game_states = self._update_states_vectorized(game_states, action_indices, betting_open)

            betting_open = self._check_betting_round_status(game_states, betting_open, street)

        if action_count == self.max_actions_per_street - 1 and cp.any(betting_open):
            logger.warning(f"Street {street} reached max actions limit. {cp.sum(betting_open)} games did not conclude.")

        game_states['pot'] += cp.sum(game_states['bets'], axis=1)

        return game_states

    def _get_info_state_hashes(self, game_states: Dict, street: int) -> List[int]:
        """Creates a fast hash for the current information state."""
        # This is a simplified hash. A real implementation would be more robust.
        # Using tuples and Python's hash is faster than string formatting.
        current_players = game_states['current_player'].get()
        max_bets = cp.max(game_states['bets'], axis=1).get()
        pots = game_states['pot'].get()
        
        return [hash((street, p, round(float(b), 2), round(float(pot), 2))) for p, b, pot in zip(current_players, max_bets, pots)]

    def _get_active_games(self, game_states: Dict, active_mask: cp.ndarray) -> Dict:
        """Filters the game states to only include the ones that are still active."""
        active_states = {}
        for key, value in game_states.items():
            if isinstance(value, cp.ndarray) and value.ndim > 0 and value.shape[0] == active_mask.shape[0]:
                active_states[key] = value[active_mask]
            else:
                active_states[key] = value
        return active_states

    def _check_betting_round_status(self, game_states: Dict, betting_open: cp.ndarray, street: int) -> cp.ndarray:
        """
        Checks which games have completed their betting round.
        """
        still_open = cp.copy(betting_open)
        if not cp.any(still_open):
            return still_open

        active_game_indices = cp.where(still_open)[0]

        active_players = game_states['active_players'][active_game_indices]
        bets = game_states['bets'][active_game_indices]
        stacks = game_states['player_stacks'][active_game_indices]
        has_acted = game_states['has_acted_this_round'][active_game_indices]

        num_active_players = cp.sum(active_players, axis=1)
        one_player_left = (num_active_players <= 1)

        can_act_mask = active_players & (stacks > 0.01)
        all_acted = cp.all(has_acted | ~can_act_mask, axis=1)

        masked_bets = cp.where(can_act_mask, bets, -1.0)
        max_bet = cp.max(masked_bets, axis=1, keepdims=True)
        bets_equal = cp.all((bets == max_bet) | ~can_act_mask, axis=1)

        bb_has_option = (street == 0) & (cp.max(bets, axis=1) <= self.big_blind)
        bb_has_acted = has_acted[:, 1]
        bb_action_is_closed = ~bb_has_option | bb_has_acted

        betting_settled = all_acted & bets_equal & bb_action_is_closed

        indices_to_close = active_game_indices[one_player_left | betting_settled]
        still_open[indices_to_close] = False

        return still_open

    def _record_history_vectorized(self, game_states: Dict, node_indices: cp.ndarray, action_indices: cp.ndarray, strategies: cp.ndarray, betting_open: cp.ndarray):
        """Record decision history in a GPU-optimized way."""
        active_game_indices = cp.where(betting_open)[0]
        if active_game_indices.size == 0:
            return

        history_counts = game_states['history_count'][active_game_indices]
        
        if cp.any(history_counts >= game_states['max_history']):
            logger.warning("Max history reached for some games. History will be truncated.")
            history_counts = cp.minimum(history_counts, game_states['max_history'] - 1)

        game_states['history_indices'][active_game_indices, history_counts] = node_indices
        game_states['history_actions'][active_game_indices, history_counts] = action_indices
        game_states['history_strategies'][active_game_indices, history_counts] = strategies
        
        game_states['history_count'][active_game_indices] += 1

    def _calculate_showdown_utilities(self, game_states: Dict) -> cp.ndarray:
        """Calculates utilities for all games that go to showdown using the GPUEquityCalculator."""
        batch_size = game_states['pot'].shape[0]
        utilities = cp.zeros((batch_size, self.num_players), dtype=cp.float32)

        num_active_players = cp.sum(game_states['active_players'], axis=1)
        showdown_mask = num_active_players > 1

        if cp.any(showdown_mask):
            showdown_hands = game_states['hands'][showdown_mask]
            showdown_board = game_states['board'][showdown_mask]
            showdown_active_players = game_states['active_players'][showdown_mask]
            showdown_pots = game_states['pot'][showdown_mask]

            win_counts = self.equity_calculator.calculate_equity_vectorized(
                showdown_hands, showdown_board, showdown_active_players
            )
            
            winners = cp.argmax(win_counts, axis=1)
            winnings = cp.zeros_like(showdown_active_players, dtype=cp.float32)
            winnings[cp.arange(winners.size), winners] = showdown_pots
            utilities[showdown_mask] = winnings

        one_player_left_mask = (num_active_players == 1)
        if cp.any(one_player_left_mask):
            pot_for_winners = game_states['pot'][one_player_left_mask]
            active_for_winners = game_states['active_players'][one_player_left_mask]
            winnings = pot_for_winners.reshape(-1, 1) * active_for_winners
            utilities[one_player_left_mask] = winnings

        return utilities

    def _update_regrets_and_strategy(self, game_states: Dict, final_utilities: cp.ndarray):
        """
        Updates regrets and strategies for all decision nodes visited during the batch,
        performing all calculations on the GPU.
        """
        batch_size, max_history = game_states['history_actions'].shape
        num_actions = game_states['history_strategies'].shape[2]

        valid_history_mask = cp.arange(max_history) < game_states['history_count'][:, None]

        utility_per_game = final_utilities.mean(axis=1, keepdims=True)
        
        cf_values = cp.zeros_like(game_states['history_strategies'])
        actions_taken = game_states['history_actions']
        
        # Manually place utility values into cf_values for the action taken
        # This is the compatible replacement for put_along_axis
        I, J = cp.ogrid[:batch_size, :max_history]
        cf_values[I, J, actions_taken] = utility_per_game

        strategies = game_states['history_strategies']
        node_values = cp.sum(strategies * cf_values, axis=2, keepdims=True)
        regrets = cf_values - node_values
        
        # Flatten all history into a single batch for the manager
        valid_indices = cp.where(valid_history_mask)
        
        node_indices_flat = game_states['history_indices'][valid_indices]
        regrets_flat = regrets[valid_indices]
        strategies_flat = strategies[valid_indices]
        
        # For now, reach_probs are simplified. A full implementation would track these.
        reach_probs_flat = cp.ones_like(regrets_flat[:, 0])

        self.strategy_manager.update_regrets_and_strategies(
            node_indices_flat,
            regrets_flat,
            strategies_flat,
            reach_probs_flat
        )

    def _sample_actions_vectorized(self, strategies: cp.ndarray) -> cp.ndarray:
        """Samples actions for a batch of games based on their strategies."""
        cumulative_strategies = cp.cumsum(strategies, axis=1)
        rand_vals = cp.random.rand(strategies.shape[0], 1)
        action_indices = cp.sum(cumulative_strategies < rand_vals, axis=1)
        return action_indices

    def _find_next_player_vectorized(self, game_states: Dict, active_mask: cp.ndarray) -> Dict:
        """
        Finds the next player in a circular fashion who is still active and has chips.
        """
        if not cp.any(active_mask):
            return game_states

        active_game_indices = cp.where(active_mask)[0]
        
        current_players = game_states['current_player'][active_game_indices]
        active_players_matrix = game_states['active_players'][active_game_indices]
        player_stacks_matrix = game_states['player_stacks'][active_game_indices]

        offsets = cp.arange(1, self.num_players + 1)
        candidate_player_indices = (current_players[:, None] + offsets) % self.num_players
        
        candidate_active = cp.take_along_axis(active_players_matrix, candidate_player_indices, axis=1)
        candidate_stacks = cp.take_along_axis(player_stacks_matrix, candidate_player_indices, axis=1)
        candidate_can_act = candidate_active & (candidate_stacks > 0.01)

        first_valid_candidate_offset = cp.argmax(candidate_can_act, axis=1)
        next_players = cp.take_along_axis(candidate_player_indices, first_valid_candidate_offset[:, None], axis=1).squeeze()

        game_states['current_player'][active_game_indices] = next_players
        
        return game_states

    def _update_states_vectorized(self, game_states: Dict, action_indices: cp.ndarray, betting_open: cp.ndarray) -> Dict:
        """
        Updates the game states for active games based on the sampled actions.
        0: Fold, 1: Call, 2: Raise
        """
        active_game_indices = cp.where(betting_open)[0]
        if active_game_indices.size == 0:
            return game_states

        current_players = game_states['current_player'][active_game_indices]
        stacks = game_states['player_stacks'][active_game_indices]
        bets = game_states['bets'][active_game_indices]

        raise_mask = (action_indices == 2)
        if cp.any(raise_mask):
            game_indices_to_raise = active_game_indices[raise_mask]
            game_states['has_acted_this_round'][game_indices_to_raise] = False

        game_states['has_acted_this_round'][active_game_indices, current_players] = True

        fold_mask = (action_indices == 0)
        if cp.any(fold_mask):
            player_indices_to_fold = current_players[fold_mask]
            game_indices_to_fold = active_game_indices[fold_mask]
            game_states['active_players'][game_indices_to_fold, player_indices_to_fold] = False

        call_mask = (action_indices == 1)
        if cp.any(call_mask):
            max_bet = cp.max(bets[call_mask], axis=1)
            current_bet = bets[call_mask, current_players[call_mask]]
            to_call = max_bet - current_bet
            amount_to_call = cp.minimum(to_call, stacks[call_mask, current_players[call_mask]])
            
            game_indices_to_call = active_game_indices[call_mask]
            player_indices_to_call = current_players[call_mask]
            
            game_states['bets'][game_indices_to_call, player_indices_to_call] += amount_to_call
            game_states['player_stacks'][game_indices_to_call, player_indices_to_call] -= amount_to_call

        if cp.any(raise_mask):
            game_indices_to_raise = active_game_indices[raise_mask]
            player_indices_to_raise = current_players[raise_mask]

            game_states['last_aggressor'][game_indices_to_raise] = player_indices_to_raise

            pot_size = game_states['pot'][game_indices_to_raise]
            bets_to_raise = bets[raise_mask]
            max_bet = cp.max(bets_to_raise, axis=1)
            current_bet = bets_to_raise[cp.arange(len(player_indices_to_raise)), player_indices_to_raise]
            to_call = max_bet - current_bet
            
            total_bet = current_bet + to_call + pot_size
            
            stacks_to_raise = stacks[raise_mask]
            amount_to_bet = cp.minimum(total_bet - current_bet, stacks_to_raise[cp.arange(len(player_indices_to_raise)), player_indices_to_raise])
            
            game_states['bets'][game_indices_to_raise, player_indices_to_raise] += amount_to_bet
            game_states['player_stacks'][game_indices_to_raise, player_indices_to_raise] -= amount_to_bet

        game_states = self._find_next_player_vectorized(game_states, betting_open)

        return game_states

    def save_strategies_to_file(self, filename: str = "strategy_table.json"):
        """Delegates saving to the strategy manager."""
        self.strategy_manager.save_strategy_table(filename)
