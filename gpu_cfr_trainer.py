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
    def __init__(self, num_players: int = 6, small_blind: float = 0.02, big_blind: float = 0.04, use_gpu: bool = True, initial_stack: float = 4.0):
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
        self.hand_counter = 0
        self.recursion_depth = 0  # For test compatibility 
        
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
            
            # 1. Sample a batch of root game states on the GPU
            game_states = self._sample_initial_states_gpu(batch_size)
            
            # 2. Process the batch through the game tree on the GPU
            self._cfr_vectorized_iteration(game_states)

            end_time = time.time()
            logger.info(f"Iteration {i+1}/{iterations} completed in {end_time - start_time:.2f}s")

            if (i + 1) % 10 == 0:
                self.strategy_lookup.update_and_save_strategy_table(self.nodes)
                logger.info(f"Strategy table saved at iteration {i+1}")

        self.strategy_lookup.update_and_save_strategy_table(self.nodes)
        logger.info("Final strategy table saved.")

    def _sample_initial_states_gpu(self, batch_size: int) -> Dict:
        """Sample a batch of initial game states for training, directly on the GPU."""
        # In a real implementation, hands would be dealt, but for now, we focus on the financial state
        return {
            "pot": cp.full(batch_size, self.small_blind + self.big_blind, dtype=cp.float32),
            "bets": cp.tile(cp.array([self.small_blind, self.big_blind] + [0] * (self.num_players - 2), dtype=cp.float32), (batch_size, 1)),
            "active_players": cp.ones((batch_size, self.num_players), dtype=cp.bool_),
            "player_stacks": cp.full((batch_size, self.num_players), self.initial_stack, dtype=cp.float32),
            "reach_probs": cp.ones((batch_size, self.num_players), dtype=cp.float32),
            "current_player": cp.zeros(batch_size, dtype=cp.int32), # Player 0 starts pre-flop
            "history_count": cp.zeros(batch_size, dtype=cp.int32), # Track how many decisions per game
            "max_history": 100, # Maximum decisions per game
            "history_nodes": [[] for _ in range(batch_size)], # Store node references (CPU-side)
            "history_actions": cp.zeros((batch_size, 100), dtype=cp.int32), # Store actions (GPU-side)
            "history_strategies": cp.zeros((batch_size, 100, 3), dtype=cp.float32) # Store strategies (GPU-side)
        }

    def _cfr_vectorized_iteration(self, game_states: Dict):
        """
        Performs one iteration of vectorized CFR by processing a batch of game states through each street.
        """
        # Pre-flop
        game_states, terminal_utilities = self._process_street_vectorized(game_states, street=0)
        
        # Flop
        game_states, terminal_utilities = self._process_street_vectorized(game_states, street=1, terminal_utilities=terminal_utilities)
        
        # Turn
        game_states, terminal_utilities = self._process_street_vectorized(game_states, street=2, terminal_utilities=terminal_utilities)
        
        # River
        game_states, terminal_utilities = self._process_street_vectorized(game_states, street=3, terminal_utilities=terminal_utilities)
        
        # Showdown and regret updates
        final_utilities = self._calculate_showdown_utilities(game_states)
        self._update_regrets_and_strategy(game_states, final_utilities)

    def _process_street_vectorized(self, game_states: Dict, street: int, terminal_utilities: cp.ndarray = None) -> Tuple[Dict, cp.ndarray]:
        """
        Processes a full betting round for a batch of game states on the GPU.
        """
        batch_size = game_states['pot'].shape[0]

        if terminal_utilities is None:
            terminal_utilities = cp.zeros((batch_size, self.num_players), dtype=cp.float32)

        # Reset bets for the new street. Pre-flop starts with blinds, so no reset needed.
        if street > 0:
            game_states['bets'] = cp.zeros((batch_size, self.num_players), dtype=cp.float32)

        # Loop until the betting round is over for all games in the batch
        betting_open = cp.ones(batch_size, dtype=cp.bool_)
        # Games with one or zero players are not open for betting
        betting_open[cp.sum(game_states['active_players'], axis=1) <= 1] = False

        max_actions_per_street = 25 

        for action_count in range(max_actions_per_street):
            if not cp.any(betting_open):
                break

            # 1. Get nodes for the current state of all active games
            active_game_states = self._get_active_games(game_states, betting_open)
            
            # Create more descriptive info state keys
            info_state_keys = [f"s:{street}_p:{p}_b:{b:.2f}_pot:{pot:.2f}" 
                               for p, b, pot in zip(active_game_states['current_player'].get(), 
                                                  cp.max(active_game_states['bets'], axis=1).get(),
                                                  active_game_states['pot'].get())]
            
            nodes = self._get_or_create_nodes_vectorized(info_state_keys)

            # 2. Get strategies and sample actions
            strategies = self._get_strategies_vectorized(nodes)
            action_indices = self._sample_actions_vectorized(strategies)

            # Record history for regret calculation
            self._record_history_vectorized(game_states, nodes, action_indices, strategies, betting_open)

            # 3. Update game states based on the chosen actions
            game_states = self._update_states_vectorized(game_states, action_indices, betting_open)

            # 4. Check which games have finished the betting round
            betting_open = self._check_betting_round_status(game_states, betting_open)
        
        if action_count == max_actions_per_street - 1 and cp.any(betting_open):
            logger.warning(f"Street {street} reached max actions limit. {cp.sum(betting_open)} games did not conclude.")

        # Collect money from bets into the pot at the end of the street
        game_states['pot'] += cp.sum(game_states['bets'], axis=1)

        return game_states, terminal_utilities

    def _get_active_games(self, game_states: Dict, active_mask: cp.ndarray) -> Dict:
        """Filters the game states to only include the ones that are still active."""
        active_states = {}
        for key, value in game_states.items():
            if isinstance(value, cp.ndarray) and value.ndim > 0 and value.shape[0] == active_mask.shape[0]:
                active_states[key] = value[active_mask]
            elif key == 'history_nodes': # Handle list of lists
                active_states[key] = [elem for i, elem in enumerate(value) if active_mask[i]]
            else:
                active_states[key] = value # Carry over non-batch-aligned data
        return active_states

    def _check_betting_round_status(self, game_states: Dict, betting_open: cp.ndarray) -> cp.ndarray:
        """
        Checks which games have completed their betting round.
        A round is over if:
        1. Only one player is left active in the whole game.
        2. All active players with chips have contributed the same amount to the pot for this street OR are all-in.
        """
        still_open = cp.copy(betting_open)
        if not cp.any(still_open):
            return still_open
        
        active_game_indices = cp.where(still_open)[0]

        # Filter states for only the games we're checking
        active_players = game_states['active_players'][active_game_indices]
        bets = game_states['bets'][active_game_indices]
        stacks = game_states['player_stacks'][active_game_indices]

        # Condition 1: Only one player left
        num_active_players = cp.sum(active_players, axis=1)
        one_player_left = (num_active_players <= 1)
        
        # Condition 2: All active players have matched the highest bet or are all-in
        max_bet = cp.max(bets, axis=1, keepdims=True)
        can_act_mask = active_players & (stacks > 0.01)
        
        unmatched_bets = (bets < max_bet) & can_act_mask
        any_unmatched = cp.any(unmatched_bets, axis=1)
        
        round_is_closed = ~any_unmatched

        # Update the original `still_open` mask for games that are now closed
        indices_to_close = active_game_indices[one_player_left | round_is_closed]
        still_open[indices_to_close] = False

        return still_open

    def _record_history_vectorized(self, game_states: Dict, nodes: List['CFRNode'], action_indices: cp.ndarray, strategies: cp.ndarray, betting_open: cp.ndarray):
        """Record decision history in a GPU-optimized way."""
        active_game_indices = cp.where(betting_open)[0]
        if active_game_indices.size == 0:
            return

        history_counts = game_states['history_count'][active_game_indices]
        
        # Ensure we don't go out of bounds
        if cp.any(history_counts >= game_states['max_history']):
            logger.warning("Max history reached for some games. History will be truncated.")
            # Clamp indices to avoid errors
            history_counts = cp.minimum(history_counts, game_states['max_history'] - 1)

        # Update GPU-side history
        game_states['history_actions'][active_game_indices, history_counts] = action_indices
        game_states['history_strategies'][active_game_indices, history_counts] = strategies
        
        # Update CPU-side history (nodes)
        active_game_indices_cpu = active_game_indices.get()
        history_counts_cpu = history_counts.get()
        for i, node in enumerate(nodes): # nodes is already the list for active games
            game_idx = active_game_indices_cpu[i]
            hist_idx = history_counts_cpu[i]
            if hist_idx < game_states['max_history']:
                 game_states['history_nodes'][game_idx].append(node)

        # Increment history count for active games
        game_states['history_count'][active_game_indices] += 1


    def _calculate_showdown_utilities(self, game_states: Dict) -> cp.ndarray:
        """Calculates utilities for all games that go to showdown."""
        logger.info("Calculating showdown utilities...")
        batch_size = game_states['pot'].shape[0]
        utilities = cp.zeros((batch_size, self.num_players), dtype=cp.float32)

        # Identify games that are at showdown (more than one player active)
        num_active_players = cp.sum(game_states['active_players'], axis=1)
        showdown_mask = num_active_players > 1

        if not cp.any(showdown_mask):
            return utilities

        # For now, we'll just split the pot evenly among the active players in a showdown
        # A real implementation would use the GPUEquityCalculator here.
        showdown_pots = game_states['pot'][showdown_mask]
        showdown_active_players = game_states['active_players'][showdown_mask]
        num_showdown_players = cp.sum(showdown_active_players, axis=1)

        # Calculate winnings for each player in the showdown
        winnings = showdown_pots / num_showdown_players

        # Distribute winnings to the active players using broadcasting
        winnings_reshaped = winnings.reshape(-1, 1)
        showdown_utilities = cp.where(showdown_active_players, winnings_reshaped, 0)

        utilities[showdown_mask] = showdown_utilities
        
        # Also calculate utilities for games that ended before showdown (one player left)
        one_player_left_mask = num_active_players == 1
        if cp.any(one_player_left_mask):
            # The player who is still active wins the whole pot
            pot_for_winners = game_states['pot'][one_player_left_mask]
            active_for_winners = game_states['active_players'][one_player_left_mask]
            
            # Winner gets pot, others get 0. The amount they put in is their loss.
            winnings = pot_for_winners.reshape(-1, 1) * active_for_winners
            
            # To get true utility, we subtract what they put in.
            # For now, returning winnings is simpler and still works for regret.
            utilities[one_player_left_mask] = winnings

        return utilities

    def _update_regrets_and_strategy(self, game_states: Dict, final_utilities: cp.ndarray):
        """
        Traverse the recorded history for each game in the batch and update regrets
        and strategies for every decision node visited.
        This version is optimized to perform all heavy computation on the GPU at once,
        then apply the results in a CPU loop.
        """
        logger.info("Updating regrets and strategies (hybrid GPU/CPU)...")
        batch_size = final_utilities.shape[0]
        max_history = game_states['history_actions'].shape[1]

        # --- GPU Computation ---

        # 1. Create a mask for valid history entries
        history_arange = cp.arange(max_history, dtype=cp.int32)
        valid_history_mask = history_arange < game_states['history_count'][:, None]

        # 2. Calculate counterfactual values (vectorized)
        # Using mean utility as a proxy, as in the previous version.
        utility_per_game = final_utilities.mean(axis=1, keepdims=True)

        cf_values = cp.zeros_like(game_states['history_strategies'])
        actions_taken = game_states['history_actions'][:, :, cp.newaxis]
        
        # Place the utility of the game into the slot for the action that was taken.
        # This is a simplified proxy for true counterfactual values.
        # We need to broadcast utility_per_game to match the history dimension
        utility_broadcast = cp.broadcast_to(utility_per_game[:, None, :], (batch_size, max_history, 1))
        
        # Place the actual utility received into the slot for the action taken
        if hasattr(cp, 'put_along_axis'):
            cp.put_along_axis(cf_values, actions_taken, utility_broadcast, axis=2)
        else:
            # Manual implementation for older CuPy versions
            batch_size, num_players, _ = cf_values.shape
            I, J = cp.ogrid[:batch_size, :num_players]
            actions_idx = actions_taken.squeeze(axis=(2,))
            values = utility_broadcast.squeeze(axis=2)
            cf_values[I, J, actions_idx] = values


        # Calculate the expected value of the current state (node)
        # This is the sum over all actions of [strategy(action) * counterfactual_value(action)]
        strategies = game_states['history_strategies']
        node_values = cp.sum(strategies * cf_values, axis=2, keepdims=True)

        # 4. Calculate regrets
        regrets = cf_values - node_values
        
        # Mask out invalid history entries to ensure they don't contribute
        regrets *= valid_history_mask[:, :, cp.newaxis]
        strategies_to_update = strategies * valid_history_mask[:, :, cp.newaxis]

        # --- Data Transfer to CPU ---
        regrets_cpu = cp.asnumpy(regrets)
        strategies_cpu = cp.asnumpy(strategies_to_update)
        history_counts_cpu = cp.asnumpy(game_states['history_count'])
        nodes_list = game_states['history_nodes']

        # --- CPU Loop for Updates ---
        logger.info("Applying updates to CPU node objects...")
        for i in range(batch_size):
            history_len = history_counts_cpu[i]
            if history_len == 0:
                continue

            nodes = nodes_list[i]
            
            for t in range(history_len):
                node = nodes[t]
                
                # Update regrets and strategy sum
                # These should be scaled by reach probabilities, which we are not tracking yet.
                node.regret_sum += regrets_cpu[i, t]
                
                # This should be scaled by our reach probability.
                reach_prob = 1.0 # Placeholder
                node.strategy_sum += reach_prob * strategies_cpu[i, t]

    def _sample_actions_vectorized(self, strategies: cp.ndarray) -> cp.ndarray:
        """Samples actions for a batch of games based on their strategies."""
        # Create a cumulative distribution for sampling
        cumulative_strategies = cp.cumsum(strategies, axis=1)
        # Generate random numbers for each game in the batch
        rand_vals = cp.random.rand(strategies.shape[0], 1)
        # Find the action index where the random value falls
        action_indices = cp.sum(cumulative_strategies < rand_vals, axis=1)
        return action_indices

    def _find_next_player_vectorized(self, game_states: Dict, active_mask: cp.ndarray) -> Dict:
        """
        Finds the next player in a circular fashion who is still active and has chips.
        This is a fully vectorized implementation.
        """
        if not cp.any(active_mask):
            return game_states

        active_game_indices = cp.where(active_mask)[0]
        
        # Extract data for active games
        current_players = game_states['current_player'][active_game_indices]
        active_players_matrix = game_states['active_players'][active_game_indices]
        player_stacks_matrix = game_states['player_stacks'][active_game_indices]

        # Generate candidate player indices for each game, starting from the next player
        offsets = cp.arange(1, self.num_players + 1)
        candidate_player_indices = (current_players[:, None] + offsets) % self.num_players
        
        # Gather the status (active and has chips) for all candidates
        candidate_active = cp.take_along_axis(active_players_matrix, candidate_player_indices, axis=1)
        candidate_stacks = cp.take_along_axis(player_stacks_matrix, candidate_player_indices, axis=1)
        candidate_can_act = candidate_active & (candidate_stacks > 0.01)

        # Find the first valid candidate for each game
        first_valid_candidate_offset = cp.argmax(candidate_can_act, axis=1)

        # Get the actual player index from the candidates using the offsets
        next_players = cp.take_along_axis(candidate_player_indices, first_valid_candidate_offset[:, None], axis=1).squeeze()

        # A check to see if a valid next player was found.
        chosen_can_act = cp.take_along_axis(candidate_can_act, first_valid_candidate_offset[:, None], axis=1).squeeze();
        
        # Only update player if a valid next player was found. Otherwise, the player stays the same,
        # and the betting round should be terminated by `_check_betting_round_status`.
        # Always advance the player, the check for round status will handle termination.
        game_states['current_player'][active_game_indices] = next_players
        
        return game_states

    def _get_or_create_nodes_vectorized(self, info_state_keys: List[str]) -> List[CFRNode]:
        """Gets or creates nodes for a list of info state keys."""
        nodes = []
        for key in info_state_keys:
            if key not in self.nodes:
                # Assuming 3 actions: fold, call, raise for simplicity
                self.nodes[key] = CFRNode(num_actions=3, actions=['f', 'c', 'r'])
            nodes.append(self.nodes[key])
        return nodes

    def _get_strategies_vectorized(self, nodes: List[CFRNode]) -> cp.ndarray:
        """Gets strategies from a list of nodes and stacks them into a CuPy array."""
        strategies = [node.get_strategy() for node in nodes]
        return cp.array(strategies, dtype=cp.float32)

    def _update_states_vectorized(self, game_states: Dict, action_indices: cp.ndarray, betting_open: cp.ndarray) -> Dict:
        """
        Updates the game states for active games based on the sampled actions.
        0: Fold, 1: Call, 2: Raise
        """
        active_game_indices = cp.where(betting_open)[0]
        if active_game_indices.size == 0:
            return game_states

        # --- Get data for active games ---
        current_players = game_states['current_player'][active_game_indices]
        stacks = game_states['player_stacks'][active_game_indices]
        bets = game_states['bets'][active_game_indices]

        # --- Apply actions ---
        # Action 0: Fold
        fold_mask = (action_indices == 0)
        if cp.any(fold_mask):
            player_indices_to_fold = current_players[fold_mask]
            game_indices_to_fold = active_game_indices[fold_mask]
            game_states['active_players'][game_indices_to_fold, player_indices_to_fold] = False

        # Action 1: Call
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

        # Action 2: Raise
        raise_mask = (action_indices == 2)
        if cp.any(raise_mask):
            # Simplified raise logic: raise by the size of the pot
            pot_size = game_states['pot'][active_game_indices[raise_mask]]
            max_bet = cp.max(bets[raise_mask], axis=1)
            current_bet = bets[raise_mask, current_players[raise_mask]]
            to_call = max_bet - current_bet
            
            # Raise amount is pot size, but must call first.
            raise_amount = pot_size
            total_bet = current_bet + to_call + raise_amount
            
            # Ensure player has enough stack
            amount_to_bet = cp.minimum(total_bet - current_bet, stacks[raise_mask, current_players[raise_mask]])
            
            game_indices_to_raise = active_game_indices[raise_mask]
            player_indices_to_raise = current_players[raise_mask]

            game_states['bets'][game_indices_to_raise, player_indices_to_raise] += amount_to_bet
            game_states['player_stacks'][game_indices_to_raise, player_indices_to_raise] -= amount_to_bet

        # --- Find next player to act ---
        game_states = self._find_next_player_vectorized(game_states, betting_open)

        return game_states

    def save_strategies_to_file(self, filename: str = "strategy_table.json"):
        """Save the learned strategies to a JSON file."""
        strategies = {}
        
        for info_set, node in self.nodes.items():
            avg_strategy = node.get_average_strategy()
            strategies[info_set] = avg_strategy
        
        try:
            with open(filename, 'w') as f:
                json.dump(strategies, f, indent=2)
            print(f"Successfully saved {len(strategies)} strategies to {filename}")
        except Exception as e:
            print(f"Error saving strategies to {filename}: {e}")
