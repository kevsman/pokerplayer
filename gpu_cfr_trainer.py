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
    def __init__(self, num_players: int = 6, small_blind: float = 0.02, big_blind: float = 0.04, use_gpu: bool = True, initial_stack: float = 4.0, dtype=cp.float16):
        self.num_players = num_players
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.initial_stack = self.big_blind * 100
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = GPUEquityCalculator(use_gpu=self.use_gpu)
        self.strategy_manager = GPUStrategyManager(dtype=dtype) # Pass dtype
        self.deck = self.equity_calculator.all_cards[:]
        self.hand_counter = 0
        self.recursion_depth = 0
        self.dtype = dtype # Store dtype
        
        # Terminal conditions - EXTREMELY AGGRESSIVE to prevent infinite loops
        self.max_recursion_depth = 50
        self.max_actions_per_street = 3   # ONLY 3 actions per street max - ultra aggressive
        self.max_total_actions = 12       # ONLY 12 total actions - force very quick games
        
        # OPTIMIZATION: Pre-allocate reusable arrays to avoid repeated memory allocation
        self._temp_arrays = {}

    def _get_info_state_hashes(self, game_states: Dict, street: int) -> List[int]:
        """CARD-INDEPENDENT: Creates hashes that match the bot's live game hash generation."""
        current_players = game_states['current_player']
        bets = game_states['bets']
        active_players = game_states['active_players']
        
        # Core betting state (must match poker_bot_v2.py exactly)
        max_bets = cp.max(bets, axis=1)
        pot_at_start_of_street = game_states['pot']
        sum_of_current_bets = cp.sum(bets, axis=1)
        effective_pots = pot_at_start_of_street + sum_of_current_bets
        
        # Enhanced state diversity (card-independent, matches bot)
        num_active = cp.sum(active_players, axis=1)
        avg_bet = cp.mean(bets, axis=1)
        
        # EXACT MATCH to poker_bot_v2.py hash generation
        street_component = street * 10000000000
        player_component = current_players.astype(cp.int64) * 1000000000
        maxbet_component = (max_bets * 100).astype(cp.int64) * 100000
        pot_component = (effective_pots * 100).astype(cp.int64) * 10
        active_component = num_active.astype(cp.int64) * 1000000
        avgbet_component = (avg_bet * 100).astype(cp.int64)
        
        # Enhanced hash combination matching the bot exactly
        combined_hash = (street_component + player_component + maxbet_component + 
                        pot_component + active_component + avgbet_component)
        
        # Apply the same enhanced mixing as the bot
        combined_hash = combined_hash * 2654435761  # Large prime
        combined_hash = combined_hash ^ (combined_hash >> 16)  # XOR folding
        combined_hash = combined_hash * 1664525  # Another prime
        combined_hash = combined_hash ^ (combined_hash >> 24)  # More folding
        combined_hash = combined_hash & 0x7FFFFFFFFFFFFFFF  # Ensure positive
        
        return combined_hash.get().tolist()

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

            # Save less frequently to prevent corruption with large files
            if (i + 1) % 200 == 0:  # Save every 200 iterations to reduce I/O
                self.strategy_manager.save_strategy_table()
                unique_states = len(self.strategy_manager.node_map)
                logger.info(f"Strategy table saved at iteration {i+1} - {unique_states} unique states encountered so far")

        self.strategy_manager.save_strategy_table()
        logger.info("Final strategy table saved.")

    def _sample_initial_states_gpu(self, batch_size: int) -> Dict:
        """
        ENHANCED: Sample diverse initial game states for maximum strategy exploration.
        Creates varied stack sizes, positions, and betting patterns to force diversity.
        """
        hands, boards = self.equity_calculator.deal_hands_and_boards_vectorized(
            num_players=self.num_players, num_games=batch_size
        )

        # DIVERSITY 1: Randomize starting positions (not always UTG first)
        random_first_player = cp.random.randint(0, self.num_players, size=batch_size, dtype=cp.int32)
        
        # DIVERSITY 2: Vary stack sizes dramatically (20BB to 200BB)
        stack_multipliers = cp.random.uniform(0.5, 5.0, size=(batch_size, self.num_players)).astype(self.dtype)
        varied_stacks = cp.full((batch_size, self.num_players), self.initial_stack, dtype=self.dtype) * stack_multipliers
        
        # DIVERSITY 3: Create different preflop scenarios
        scenario_type = cp.random.randint(0, 4, size=batch_size)  # 4 different starting scenarios
        
        # Scenario 0: Standard UTG start
        standard_bets = cp.tile(cp.array([self.small_blind, self.big_blind] + [0] * (self.num_players - 2), dtype=self.dtype), (batch_size, 1))
        standard_pot = cp.full(batch_size, self.small_blind + self.big_blind, dtype=self.dtype)
        
        # Scenario 1: Someone already raised preflop (3-bet pot)
        raised_bets = cp.copy(standard_bets)
        raise_amount = self.big_blind * 3  # 3BB raise
        raise_positions = cp.random.randint(2, self.num_players, size=batch_size)  # Random raiser
        for i in range(batch_size):
            if scenario_type[i] == 1:
                raised_bets[i, raise_positions[i]] = raise_amount
        raised_pot = cp.sum(raised_bets, axis=1)
        
        # Scenario 2: Multiple players limped in
        limped_bets = cp.copy(standard_bets)
        num_limpers = cp.random.randint(2, 5, size=batch_size)  # 2-4 limpers
        for i in range(batch_size):
            if scenario_type[i] == 2:
                for j in range(2, min(2 + int(num_limpers[i]), self.num_players)):
                    limped_bets[i, j] = self.big_blind  # Everyone calls
        limped_pot = cp.sum(limped_bets, axis=1)
        
        # Scenario 3: 4-bet pot (very aggressive)
        fourbet_bets = cp.copy(standard_bets)
        fourbet_amount = self.big_blind * 12  # 12BB 4-bet
        fourbet_positions = cp.random.randint(0, self.num_players, size=batch_size)
        for i in range(batch_size):
            if scenario_type[i] == 3:
                fourbet_bets[i, fourbet_positions[i]] = fourbet_amount
        fourbet_pot = cp.sum(fourbet_bets, axis=1)
        
        # Combine scenarios based on scenario_type
        final_bets = cp.where(scenario_type[:, None] == 0, standard_bets, 
                     cp.where(scenario_type[:, None] == 1, raised_bets,
                     cp.where(scenario_type[:, None] == 2, limped_bets, fourbet_bets)))
        
        final_pot = cp.where(scenario_type == 0, standard_pot,
                    cp.where(scenario_type == 1, raised_pot,
                    cp.where(scenario_type == 2, limped_pot, fourbet_pot)))
        
        # DIVERSITY 4: Some players have already acted in complex scenarios
        has_acted = cp.zeros((batch_size, self.num_players), dtype=cp.bool_)
        for i in range(batch_size):
            if scenario_type[i] > 0:  # In raised/limped/4-bet scenarios, mark some as acted
                num_acted = min(int(scenario_type[i]) + 1, self.num_players - 1)
                has_acted[i, :num_acted] = True
        
        # DIVERSITY 5: Occasionally remove some players (simulate folds)
        active_players = cp.ones((batch_size, self.num_players), dtype=cp.bool_)
        fold_probability = 0.2  # 20% chance someone folded
        should_fold = cp.random.random((batch_size, self.num_players)) < fold_probability
        # Don't fold SB/BB or current player
        should_fold[:, 0] = False  # Keep SB
        should_fold[:, 1] = False  # Keep BB
        should_fold[cp.arange(batch_size), random_first_player] = False  # Keep current player
        active_players = active_players & (~should_fold)

        return {
            "pot": final_pot,
            "bets": final_bets,
            "active_players": active_players,
            "player_stacks": varied_stacks,
            "reach_probs": cp.ones((batch_size, self.num_players), dtype=cp.float32),
            "current_player": random_first_player,
            "last_aggressor": cp.full(batch_size, 1, dtype=cp.int32),
            "has_acted_this_round": has_acted,
            "history_count": cp.zeros(batch_size, dtype=cp.int32),
            "max_history": 100,
            "history_indices": cp.zeros((batch_size, 100), dtype=cp.int32),
            "history_actions": cp.zeros((batch_size, 100), dtype=cp.int32),
            "history_strategies": cp.zeros((batch_size, 100, 6), dtype=self.dtype),
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

        # --- Street Transition Logic ---
        # If moving to a new street (flop, turn, river), reset betting state for games that are still active.
        if street > 0:
            # Identify games with more than one player still active.
            active_for_street_mask = cp.sum(game_states['active_players'], axis=1) > 1
            
            if cp.any(active_for_street_mask):
                # Get the indices of the games that are continuing.
                reset_indices = cp.where(active_for_street_mask)[0]
                
                # Reset bets to zero for the new street.
                game_states['bets'][reset_indices] = 0
                
                # Reset the 'has_acted' tracker for all players in these games.
                game_states['has_acted_this_round'][reset_indices] = False
                
                # The first player to act is the first active player left of the dealer.
                # This is a simplification; a full implementation would use the small blind position.
                game_states['last_aggressor'][reset_indices] = -1 # No aggressor yet on the new street.
                active_players_to_reset = game_states['active_players'][reset_indices]
                first_to_act = cp.argmax(active_players_to_reset, axis=1).astype(cp.int32)
                game_states['current_player'][reset_indices] = first_to_act

        betting_open = cp.ones(batch_size, dtype=cp.bool_)
        # Games with 1 or 0 players are not open for betting.
        betting_open[cp.sum(game_states['active_players'], axis=1) <= 1] = False

        # Allow more actions on post-flop streets for realistic play
        max_actions_this_street = 3 if street == 0 else 6  # 3 for preflop, 6 for post-flop
        
        for action_count in range(max_actions_this_street):
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

        if action_count == max_actions_this_street - 1 and cp.any(betting_open):
            logger.warning(f"Street {street} reached max actions limit. {cp.sum(betting_open)} games did not conclude.")

        # The pot for the next street is the current pot plus all bets from this street.
        game_states['pot'] += cp.sum(game_states['bets'], axis=1)

        return game_states

    def _get_info_state_hashes_old(self, game_states: Dict, street: int) -> List[int]:
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
        ULTRA SIMPLE: Just close betting rounds aggressively to prevent infinite loops.
        """
        still_open = cp.copy(betting_open)
        if not cp.any(still_open):
            return still_open

        active_game_indices = cp.where(still_open)[0]
        if len(active_game_indices) == 0:
            return still_open

        active_players = game_states['active_players'][active_game_indices]
        bets = game_states['bets'][active_game_indices]
        has_acted = game_states['has_acted_this_round'][active_game_indices]
        stacks = game_states['player_stacks'][active_game_indices]

        # SIMPLE CONDITION 1: Only one player left
        num_active_players = cp.sum(active_players, axis=1)
        one_player_left = (num_active_players <= 1)

        # SIMPLE CONDITION 2: Everyone has acted at least once AND bets are reasonably close
        # This is much more permissive - we don't require exact bet equality
        all_acted = cp.all(has_acted | (~active_players), axis=1)
        
        # SIMPLE CONDITION 3: All-in situation (no one has enough chips to bet)
        can_bet = active_players & (stacks > self.big_blind * 0.5)
        no_one_can_bet = cp.sum(can_bet, axis=1) <= 1

        # ULTRA AGGRESSIVE: Close betting if ANY condition is met or if there's been any betting
        any_betting = cp.sum(bets, axis=1) > 0
        
        # Close games that meet ANY condition
        should_close = one_player_left | all_acted | no_one_can_bet | any_betting
        
        indices_to_close = active_game_indices[should_close]
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
        """OPTIMIZED: Calculates utilities with early termination and reduced equity calculations."""
        batch_size = game_states['pot'].shape[0]
        utilities = cp.zeros((batch_size, self.num_players), dtype=self.dtype)

        num_active_players = cp.sum(game_states['active_players'], axis=1)
        
        # OPTIMIZATION: Handle single-player games first (most common case)
        one_player_left_mask = (num_active_players == 1)
        if cp.any(one_player_left_mask):
            pot_for_winners = game_states['pot'][one_player_left_mask]
            active_for_winners = game_states['active_players'][one_player_left_mask]
            winnings = pot_for_winners.reshape(-1, 1) * active_for_winners
            utilities[one_player_left_mask] = winnings

        # OPTIMIZATION: Only calculate equity for multi-player showdowns (less common)
        showdown_mask = num_active_players > 1
        if cp.any(showdown_mask):
            showdown_count = cp.sum(showdown_mask)
            # OPTIMIZATION: Skip equity calculation for very small pots (not worth the compute)
            large_pot_mask = game_states['pot'][showdown_mask] > (self.big_blind * 2)
            
            if cp.any(large_pot_mask):
                large_pot_indices = cp.where(showdown_mask)[0][large_pot_mask]
                showdown_hands = game_states['hands'][large_pot_indices]
                showdown_board = game_states['board'][large_pot_indices]
                showdown_active_players = game_states['active_players'][large_pot_indices]
                showdown_pots = game_states['pot'][large_pot_indices]

                win_counts = self.equity_calculator.calculate_equity_vectorized(
                    showdown_hands, showdown_board, showdown_active_players
                )
                
                winners = cp.argmax(win_counts, axis=1)
                winnings = cp.zeros_like(showdown_active_players, dtype=self.dtype)
                winnings[cp.arange(winners.size), winners] = showdown_pots
                utilities[large_pot_indices] = winnings
            
            # OPTIMIZATION: For small pots, just split evenly (much faster)
            small_pot_indices = cp.where(showdown_mask)[0][~large_pot_mask] if cp.any(large_pot_mask) else cp.where(showdown_mask)[0]
            if small_pot_indices.size > 0:
                for idx in small_pot_indices:
                    active_players = game_states['active_players'][idx]
                    num_active = cp.sum(active_players)
                    if num_active > 0:
                        split_amount = game_states['pot'][idx] / num_active
                        utilities[idx] = active_players * split_amount

        return utilities.astype(cp.float32)

    def _update_regrets_and_strategy(self, game_states: Dict, final_utilities: cp.ndarray):
        """OPTIMIZED: Updates regrets and strategies with reduced memory allocation."""
        batch_size, max_history = game_states['history_actions'].shape

        valid_history_mask = cp.arange(max_history) < game_states['history_count'][:, None]
        
        # OPTIMIZATION: Only process games that have meaningful history
        games_with_history = game_states['history_count'] > 0
        if not cp.any(games_with_history):
            return

        # OPTIMIZATION: Use mean utility per game (simplified but much faster)
        utility_per_game = final_utilities.mean(axis=1, keepdims=True)
        
        # OPTIMIZATION: Pre-allocate cf_values with the right shape
        cf_values = cp.zeros_like(game_states['history_strategies'])
        actions_taken = game_states['history_actions']
        
        # Vectorized assignment of utilities to actions taken
        I, J = cp.ogrid[:batch_size, :max_history]
        cf_values[I, J, actions_taken] = utility_per_game

        strategies = game_states['history_strategies']
        node_values = cp.sum(strategies * cf_values, axis=2, keepdims=True)
        regrets = cf_values - node_values
        
        # OPTIMIZATION: Only flatten and update valid entries
        valid_indices = cp.where(valid_history_mask)
        
        if valid_indices[0].size > 0:  # Only update if there are valid entries
            node_indices_flat = game_states['history_indices'][valid_indices]
            regrets_flat = regrets[valid_indices]
            strategies_flat = strategies[valid_indices]
            reach_probs_flat = cp.ones(regrets_flat.shape[0], dtype=cp.float32)  # Simplified reach probs

            self.strategy_manager.update_regrets_and_strategies(
                node_indices_flat,
                regrets_flat,
                strategies_flat,
                reach_probs_flat
            )

    def _sample_actions_vectorized(self, strategies: cp.ndarray) -> cp.ndarray:
        """
        ENHANCED: Samples actions with exploration for maximum diversity.
        Occasionally forces suboptimal actions to explore more game tree branches.
        """
        batch_size = strategies.shape[0]
        
        # 90% of the time, use normal strategy-based sampling
        # 10% of the time, force random exploration
        exploration_probability = 0.1
        should_explore = cp.random.random(batch_size) < exploration_probability
        
        # Normal strategy-based sampling
        cumulative_strategies = cp.cumsum(strategies, axis=1)
        rand_vals = cp.random.rand(batch_size, 1)
        strategic_actions = cp.sum(cumulative_strategies < rand_vals, axis=1)
        
        # Forced exploration: completely random actions
        random_actions = cp.random.randint(0, strategies.shape[1], size=batch_size)
        
        # Choose between strategic and random actions
        final_actions = cp.where(should_explore, random_actions, strategic_actions)
        
        return final_actions

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
        ENHANCED: Updates the game states for active games based on the sampled actions.
        6-Action System: 0: Fold, 1: Call, 2: Raise 33% pot, 3: Raise 66% pot, 4: Raise 100% pot, 5: All-in
        """
        active_game_indices = cp.where(betting_open)[0]
        if active_game_indices.size == 0:
            return game_states

        current_players = game_states['current_player'][active_game_indices]
        stacks = game_states['player_stacks'][active_game_indices]
        bets = game_states['bets'][active_game_indices]

        # Mark current player as having acted (for all actions)
        game_states['has_acted_this_round'][active_game_indices, current_players] = True

        # HANDLE FOLDS (Action 0)
        fold_mask = (action_indices == 0)
        if cp.any(fold_mask):
            player_indices_to_fold = current_players[fold_mask]
            game_indices_to_fold = active_game_indices[fold_mask]
            game_states['active_players'][game_indices_to_fold, player_indices_to_fold] = False

        # HANDLE CALLS (Action 1)
        call_mask = (action_indices == 1)
        if cp.any(call_mask):
            call_indices = active_game_indices[call_mask]
            call_players = current_players[call_mask]
            
            max_bet = cp.max(bets[call_mask], axis=1)
            current_bet = bets[call_mask, call_players]
            to_call = cp.maximum(0, max_bet - current_bet)
            amount_to_call = cp.minimum(to_call, stacks[call_mask, call_players])
            
            game_states['bets'][call_indices, call_players] += amount_to_call.astype(self.dtype)
            game_states['player_stacks'][call_indices, call_players] -= amount_to_call.astype(self.dtype)

        # HANDLE RAISES (Actions 2, 3, 4, 5) - Multiple raise sizes for strategic depth
        for action_idx in range(2, 6):
            raise_mask = (action_indices == action_idx)
            if not cp.any(raise_mask):
                continue
                
            raise_indices = active_game_indices[raise_mask]
            raise_players = current_players[raise_mask]

            # Update last aggressor
            game_states['last_aggressor'][raise_indices] = raise_players

            # Calculate pot-based raise amounts
            current_pot = game_states['pot'][raise_indices] + cp.sum(bets[raise_mask], axis=1)
            max_bet_in_round = cp.max(bets[raise_mask], axis=1)
            current_player_bet = bets[raise_mask, raise_players]
            
            if action_idx == 2:  # 33% pot raise
                target_bet = max_bet_in_round + (current_pot * 0.33)
            elif action_idx == 3:  # 66% pot raise  
                target_bet = max_bet_in_round + (current_pot * 0.66)
            elif action_idx == 4:  # 100% pot raise
                target_bet = max_bet_in_round + current_pot
            else:  # action_idx == 5: All-in
                target_bet = current_player_bet + stacks[raise_mask, raise_players]
            
            # Calculate actual raise amount (difference from current bet to target)
            raise_amount = cp.maximum(0, target_bet - current_player_bet)
            
            # Don't let them bet more than their stack
            available_stack = stacks[raise_mask, raise_players]
            actual_raise = cp.minimum(raise_amount, available_stack)
            
            # Ensure minimum raise of at least 1 big blind
            actual_raise = cp.maximum(actual_raise, self.big_blind)
            actual_raise = cp.minimum(actual_raise, available_stack)
            
            game_states['bets'][raise_indices, raise_players] += actual_raise.astype(self.dtype)
            game_states['player_stacks'][raise_indices, raise_players] -= actual_raise.astype(self.dtype)
            
            # When someone raises, others need to act again
            game_states['has_acted_this_round'][raise_indices] = False
            game_states['has_acted_this_round'][raise_indices, raise_players] = True

        # Find next player to act
        game_states = self._find_next_player_vectorized(game_states, betting_open)

        return game_states

    def save_strategies_to_file(self, filename: str = "strategy_table.json"):
        """Delegates saving to the strategy manager."""
        self.strategy_manager.save_strategy_table(filename)
