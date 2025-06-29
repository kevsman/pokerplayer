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
        self.state_history = set()  # Track visited states
        
        # Terminal conditions
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
            "history": [[] for _ in range(batch_size)] # To track nodes and actions
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
        self._update_regrets_and_strategies(game_states, final_utilities)

    def _process_street_vectorized(self, game_states: Dict, street: int, terminal_utilities: cp.ndarray = None) -> Tuple[Dict, cp.ndarray]:
        """
        Processes a full betting round for a batch of game states on the GPU.
        """
        logger.info(f"Processing street {street} for {game_states['pot'].shape[0]} states.")

        if terminal_utilities is None:
            terminal_utilities = cp.zeros((game_states['pot'].shape[0], self.num_players), dtype=cp.float32)

        # Loop until the betting round is over for all games in the batch
        max_actions_this_street = 10 # Safety break
        for _ in range(max_actions_this_street):
            batch_size = game_states['pot'].shape[0]
            active_mask = cp.ones(batch_size, dtype=cp.bool_)

            # Check which games in the batch still need action
            # (e.g., more than one player is active and not all-in)
            # This is a simplified check
            num_active_players = cp.sum(game_states['active_players'], axis=1)
            betting_open = num_active_players > 1

            if not cp.any(betting_open):
                break # End of street for all games

            # 1. Get nodes for the current state of all games in the batch
            info_state_keys = [f"street_{street}_player_{p}" for p in game_states['current_player'].get()]
            nodes = self._get_or_create_nodes_vectorized(info_state_keys)

            # 2. Get strategies for the current player in each game
            strategies = self._get_strategies_vectorized(nodes)

            # 3. Choose an action based on the strategy
            action_indices = self._sample_actions_vectorized(strategies)

            # 4. Update game states based on the chosen actions
            game_states = self._update_states_vectorized(game_states, action_indices)

            # 5. Record the history for this decision point
            for i in range(batch_size):
                if betting_open[i]:
                    game_states['history'][i].append((nodes[i], action_indices[i].item(), strategies[i].get()))

        logger.info(f"Finished processing street {street}.")
        return game_states, terminal_utilities

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
        # Reshape winnings to (batch_size, 1) to broadcast across the players dimension
        winnings_reshaped = winnings.reshape(-1, 1)
        showdown_utilities = cp.where(showdown_active_players, winnings_reshaped, 0)

        utilities[showdown_mask] = showdown_utilities
        return utilities

    def _update_regrets_and_strategies(self, game_states: Dict, final_utilities: cp.ndarray):
        """Updates regrets and strategies based on the final utilities by backpropagating through the history."""
        logger.info("Updating regrets and strategies...")

        for i in range(len(game_states['history'])):
            player_history = game_states['history'][i]
            if not player_history:
                continue

            # The utility for the current player
            player_utility = final_utilities[i, game_states['current_player'][i]]

            for node, action_taken, strategy in reversed(player_history):
                # Calculate counterfactual values for all actions
                # This is a simplified calculation. A real implementation would be more complex.
                action_utilities = np.zeros(node.num_actions)
                action_utilities[action_taken] = player_utility.get()

                # Update regrets
                regret = action_utilities - np.sum(strategy * action_utilities)
                node.regret_sum += regret

                # Update strategy sum
                node.strategy_sum += strategy

    def _sample_actions_vectorized(self, strategies: cp.ndarray) -> cp.ndarray:
        """Sample actions from the strategies for a batch of states."""
        # Create a random matrix for sampling
        rand_vals = cp.random.rand(strategies.shape[0], 1)
        
        # Get cumulative sum of strategies
        cumulative_strategies = cp.cumsum(strategies, axis=1)
        
        # Find the action where the random value falls
        action_indices = cp.sum(rand_vals > cumulative_strategies, axis=1).astype(cp.int32)
        return action_indices

    def _get_or_create_nodes_vectorized(self, info_state_keys: List[str]) -> List[CFRNode]:
        """Gets or creates CFR nodes for a batch of information state keys."""
        nodes_batch = []
        for key in info_state_keys:
            if key not in self.nodes:
                # Assuming a fixed number of actions for simplicity [Fold, Call, Raise]
                self.nodes[key] = CFRNode(num_actions=3, actions=['Fold', 'Call', 'Raise'])
            nodes_batch.append(self.nodes[key])
        return nodes_batch

    def _get_strategies_vectorized(self, nodes: List[CFRNode]) -> cp.ndarray:
        """Gathers strategies from a batch of nodes into a single CuPy array."""
        strategies = [node.get_strategy() for node in nodes]
        return cp.array(strategies, dtype=cp.float32)

    def _update_states_vectorized(self, game_states: Dict, action_indices: cp.ndarray) -> Dict:
        """
        Updates the batch of game states based on the actions taken (0: Fold, 1: Call, 2: Raise).
        """
        batch_size = game_states['pot'].shape[0]
        current_player_indices = game_states['current_player']

        # --- Handle Folds (action_index == 0) ---
        fold_mask = (action_indices == 0)
        if cp.any(fold_mask):
            # Set the current player to inactive
            game_states['active_players'][fold_mask, current_player_indices[fold_mask]] = False

        # --- Handle Calls (action_index == 1) ---
        call_mask = (action_indices == 1)
        if cp.any(call_mask):
            max_bet = cp.max(game_states['bets'][call_mask], axis=1)
            current_bet = game_states['bets'][call_mask, current_player_indices[call_mask]]
            call_amount = max_bet - current_bet
            
            # Ensure players don't bet more than they have
            callable_amount = cp.minimum(call_amount, game_states['player_stacks'][call_mask, current_player_indices[call_mask]])

            game_states['player_stacks'][call_mask, current_player_indices[call_mask]] -= callable_amount
            game_states['bets'][call_mask, current_player_indices[call_mask]] += callable_amount
            game_states['pot'][call_mask] += callable_amount

        # --- Handle Raises (action_index == 2) ---
        raise_mask = (action_indices == 2)
        if cp.any(raise_mask):
            # Simplified raise logic: Raise by a fixed amount (e.g., pot size)
            # A real implementation would have more nuanced raise sizing.
            max_bet = cp.max(game_states['bets'][raise_mask], axis=1)
            raise_amount = game_states['pot'][raise_mask] # Pot-sized raise

            # Ensure players don't bet more than they have
            raisable_amount = cp.minimum(raise_amount, game_states['player_stacks'][raise_mask, current_player_indices[raise_mask]])

            game_states['player_stacks'][raise_mask, current_player_indices[raise_mask]] -= raisable_amount
            game_states['bets'][raise_mask, current_player_indices[raise_mask]] += raisable_amount
            game_states['pot'][raise_mask] += raisable_amount

        # --- Advance to the next player ---
        # This needs to be a robust function that finds the next active player.
        # For now, we'll use a simplified increment.
        game_states['current_player'] = (game_states['current_player'] + 1) % self.num_players

        return game_states

    def _cfr_recursive(self, player_hands, history, board, pot, bets, reach_probs,
                       active_players, player_stacks, street, num_actions_this_street, 
                       recursion_depth, total_actions=0):
        
        # Set for test compatibility
        self.recursion_depth = recursion_depth
        
        # Multiple terminal conditions for robustness
        if recursion_depth > self.max_recursion_depth:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
        
        if num_actions_this_street > self.max_actions_per_street:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
        
        if total_actions > self.max_total_actions:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
        
        # Check for state loops
        state_key = self._state_key(player_hands, board, pot, bets, active_players, player_stacks, street, num_actions_this_street)
        if state_key in self.state_history:
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
        self.state_history.add(state_key)
        
        try:
            # Count active players with chips
            active_with_chips = np.sum(active_players & (player_stacks > 0.01))
            
            # Terminal: Only one player left or no one can act
            if active_with_chips <= 1:
                return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
            
            # Check if betting round is over
            is_over = self._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
            
            if is_over:
                if street >= 3:  # River completed
                    return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
                else:
                    return self._handle_new_street(player_hands, board, pot, bets, reach_probs,
                                                   active_players, player_stacks, street, recursion_depth, total_actions)
            
            # Get current player
            player = self._get_current_player(history, active_players, street, pot, num_actions_this_street, player_stacks)
            if player == -1:
                return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
            
            # Get available actions
            actions = self._get_available_actions(player, bets, player_stacks)
            if not actions:
                return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
            
            # Create information set (avoiding numpy array conversion issues)
            bets_str = "_".join([f"{b:.2f}" for b in bets])
            info_set = f"{street}_{bets_str}_{player_stacks[player]:.2f}_{''.join(sorted(actions))}"
            
            strategy = self._get_strategy(info_set, actions)
            
            node_utility_vector = np.zeros(self.num_players)
            cf_values_for_player = np.zeros(len(actions))
            
            for i, action in enumerate(actions):
                new_history = history + action
                new_bets = bets.copy()
                new_stacks = player_stacks.copy()
                new_active_players = active_players.copy()
                new_num_actions = num_actions_this_street + 1
                new_pot = pot
                
                # Apply action
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
                        new_stacks[player] -= (new_bets[player] - bets[player])
                    else:
                        # All-in if can't raise properly
                        new_bets[player] += new_stacks[player]
                        new_stacks[player] = 0
                elif action == 'k':
                    pass  # Check, no betting change
                
                new_reach_probs = reach_probs.copy()
                new_reach_probs[player] *= strategy[i]
                
                utility = self._cfr_recursive(
                    player_hands, new_history, board, new_pot, new_bets,
                    new_reach_probs, new_active_players, new_stacks,
                    street, new_num_actions, recursion_depth + 1, total_actions + 1
                )
                
                node_utility_vector += strategy[i] * utility
                cf_values_for_player[i] = utility[player]
            
            # Update regret and strategy
            node = self.get_node(info_set, actions)
            regret = cf_values_for_player - np.sum(strategy * cf_values_for_player)
            node.regret_sum += regret
            node.strategy_sum += reach_probs[player] * strategy
            
            return node_utility_vector
            
        finally:
            # Clean up state tracking
            self.state_history.discard(state_key)

    def _is_betting_round_over(self, history: str, bets: np.ndarray, active_players: np.ndarray, 
                               street: int, num_actions: int, stacks: np.ndarray) -> bool:
        # Simple but robust conditions
        active_with_chips = active_players & (stacks > 0.01)
        num_active_with_chips = np.sum(active_with_chips)
        
        # Round over if only one player can act
        if num_active_with_chips <= 1:
            return True
        
        # Round over if no actions taken and it's not preflop
        if num_actions == 0 and street > 0:
            return True
        
        # Round over if everyone has acted and bets are equal (or players are all-in)
        if num_actions >= np.sum(active_players):
            # Check if all active players have equal bets or are all-in
            active_bets = bets[active_players]
            all_equal_or_allin = True
            
            for i in range(self.num_players):
                if not active_players[i]:
                    continue
                if stacks[i] > 0.01 and bets[i] < np.max(active_bets):
                    all_equal_or_allin = False
                    break
            
            # Special case for preflop: if BB has acted (checked/raised) after everyone else, round is over
            if street == 0 and num_actions >= np.sum(active_players):
                # Check if this looks like "SB call, BB check" scenario
                if 'c' in history and 'k' in history and 'r' not in history:
                    return True
            
            if all_equal_or_allin:
                return True
        
        # Emergency brake for too many actions
        if num_actions > self.max_actions_per_street:
            return True
        
        return False

    def _handle_new_street(self, player_hands, board, pot, bets, reach_probs, 
                           active_players, player_stacks, street, recursion_depth, total_actions):
        # Terminal if only one active player
        if np.sum(active_players) <= 1:
            return self._get_terminal_utility(player_hands, board, pot + np.sum(bets), 
                                              np.zeros(self.num_players), active_players, player_stacks)
        
        new_street = street + 1
        pot += np.sum(bets)
        new_bets = np.zeros(self.num_players)
        new_board = board[:]
        
        # Deal cards for new street
        dealt_cards = [c for hand in player_hands for c in hand] + board
        remaining_deck = [c for c in self.deck if c not in dealt_cards]
        random.shuffle(remaining_deck)
        
        cards_to_deal = 0
        if new_street == 1:  # Flop
            cards_to_deal = 3
        elif new_street in [2, 3]:  # Turn/River
            cards_to_deal = 1
        
        if cards_to_deal > 0 and len(remaining_deck) >= cards_to_deal:
            new_board.extend(remaining_deck[:cards_to_deal])
        
        return self._cfr_recursive(player_hands, "", new_board, pot, new_bets, reach_probs, 
                                   active_players, player_stacks, new_street, 0, recursion_depth + 1, total_actions)

    def _get_current_player(self, history, active_players, street, pot, num_actions_this_street, player_stacks) -> int:
        # Find players who can act
        can_act = active_players & (player_stacks > 0.01)
        active_indices = np.where(can_act)[0]
        
        if len(active_indices) == 0:
            return -1
        
        if len(active_indices) == 1:
            return active_indices[0]
        
        # Determine starting position
        if street == 0:  # Preflop
            start_pos = 2 if self.num_players > 2 else 0
        else:  # Postflop
            start_pos = 0
        
        # Find the next player to act
        current_player = start_pos
        for _ in range(num_actions_this_street):
            current_player = (current_player + 1) % self.num_players
            while not can_act[current_player]:
                current_player = (current_player + 1) % self.num_players
                if current_player == start_pos:  # Full loop
                    return -1
        
        # Ensure the current player can actually act
        if not can_act[current_player]:
            # Find next player who can act
            for i in range(self.num_players):
                next_player = (current_player + i) % self.num_players
                if can_act[next_player]:
                    return next_player
            return -1
        
        return current_player

    def _get_available_actions(self, player: int, bets: np.ndarray, stacks: np.ndarray) -> List[str]:
        actions = []
        
        if stacks[player] <= 0.01:  # No chips
            return []
        
        max_bet = np.max(bets)
        to_call = max_bet - bets[player]
        
        if to_call > 0.01:  # Need to call
            actions.extend(['f', 'c'])
            if stacks[player] > to_call + 0.01:  # Can raise
                actions.append('r')
        else:  # Can check
            actions.append('k')
            if stacks[player] > 0.01:  # Can bet/raise
                actions.append('r')
        
        return actions

    def _get_terminal_utility(self, player_hands, board, pot, bets, active_players, player_stacks) -> np.ndarray:
        investment = self.initial_stack - player_stacks
        total_pot = pot + np.sum(bets)
        
        # If only one active player, they win everything
        active_indices = np.where(active_players)[0]
        if len(active_indices) == 1:
            winnings = np.zeros(self.num_players)
            winnings[active_indices[0]] = total_pot
            return winnings - investment
        
        # Otherwise, split pot equally among active players (simplified)
        winnings = np.zeros(self.num_players)
        if len(active_indices) > 0:
            share = total_pot / len(active_indices)
            for idx in active_indices:
                winnings[idx] = share
        
        return winnings - investment

    def get_node(self, info_set: str, actions: List[str]) -> CFRNode:
        if info_set not in self.nodes:
            self.nodes[info_set] = CFRNode(len(actions), actions)
        return self.nodes[info_set]

    def _get_strategy(self, info_set: str, actions: List[str]) -> np.ndarray:
        node = self.get_node(info_set, actions)
        return node.get_strategy()

    def train_like_fixed_cfr(self, iterations: int):
        """Run CFR training for the specified number of iterations."""
        logger.info(f"Starting robust CFR training for {iterations} iterations...")
        
        for iteration in range(iterations):
            logger.info(f"Running CFR iteration {iteration + 1}/{iterations}")
            
            # Reset state tracking for each iteration
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
                    active_players, player_stacks, street=0, 
                    num_actions_this_street=0, recursion_depth=0, total_actions=0
                )
                print(f"Iteration {iteration + 1} completed successfully. Utility: {utility}")
            except Exception as e:
                print(f"Error in iteration {iteration + 1}: {e}")
                continue
        
        print(f"CFR training completed after {iterations} iterations.")
        print(f"Total nodes created: {len(self.nodes)}")
        return len(self.nodes)

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
