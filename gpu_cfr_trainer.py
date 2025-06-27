"""
GPU-accelerated CFR trainer for poker bot.
This version implements a recursive CFR algorithm for No-Limit Hold'em,
supporting up to 6 players and configurable blinds. It's based on the principles
from the article: https://medium.com/@olegostroumov/worlds-first-poker-solver-6b1dbe80d0ee
but adapted for the more complex game of No-Limit Hold'em.
"""
import numpy as np
import logging
import random
from typing import Dict, List, Tuple

# Setup logger
logger = logging.getLogger(__name__)

# Try to import GPU libraries
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logger.info("CuPy available for GPU-accelerated CFR training")
except ImportError:
    cp = None
    GPU_AVAILABLE = False
    logger.info("CuPy not available - using CPU for CFR training")

class CFRNode:
    """A node in the CFR game tree, representing an information set."""
    def __init__(self, num_actions: int, actions: List[str]):
        self.num_actions = num_actions
        self.actions = actions
        self.regret_sum = np.zeros(num_actions)
        self.strategy_sum = np.zeros(num_actions)
        self.strategy = np.repeat(1/num_actions, num_actions)

    def get_strategy(self) -> np.ndarray:
        """Get the current strategy from the regret sums using regret matching."""
        self.strategy = np.maximum(0, self.regret_sum)
        normalizing_sum = np.sum(self.strategy)
        if normalizing_sum > 0:
            self.strategy /= normalizing_sum
        else:
            self.strategy = np.repeat(1/self.num_actions, self.num_actions)
        return self.strategy

    def get_average_strategy(self) -> Dict[str, float]:
        """Get the average strategy over all iterations."""
        normalizing_sum = np.sum(self.strategy_sum)
        if normalizing_sum > 0:
            avg_strategy = self.strategy_sum / normalizing_sum
        else:
            avg_strategy = np.repeat(1/self.num_actions, self.num_actions)
        return {self.actions[i]: avg_strategy[i] for i in range(self.num_actions)}

class GPUCFRTrainer:
    """A CFR trainer for No-Limit Hold'em."""
    def __init__(self, use_gpu=True, num_players=6, small_blind=0.02, big_blind=0.04):
        self.num_players = num_players
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.small_blind = small_blind
        self.big_blind = big_blind
        
        from gpu_accelerated_equity import GPUEquityCalculator
        from hand_evaluator import HandEvaluator
        from strategy_lookup import StrategyLookup

        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = GPUEquityCalculator(use_gpu=self.use_gpu)
        self.strategy_lookup = StrategyLookup()
        
        self.nodes: Dict[str, CFRNode] = {}
        self.deck = self.equity_calculator.all_cards[:]
        
        logger.info(f"GPUCFRTrainer for NLHE initialized. Players: {num_players}, Blinds: {small_blind}/{big_blind}, GPU: {self.use_gpu}")

    def get_node(self, info_set: str, actions: List[str]) -> CFRNode:
        """Retrieve or create a CFRNode for a given information set."""
        if info_set not in self.nodes:
            self.nodes[info_set] = CFRNode(len(actions), actions)
        return self.nodes[info_set]

    def train_like_fixed_cfr(self, iterations: int):
        """Run the CFR training for NLHE."""
        logger.info(f"🚀 Starting NLHE CFR training for {iterations} iterations...")
        
        for i in range(iterations):
            if (i + 1) % 100 == 0:
                logger.info(f"  Iteration {i + 1}/{iterations}...")
            
            random.shuffle(self.deck)
            player_hands = [self.deck[j*2:j*2+2] for j in range(self.num_players)]
            
            active_players = np.ones(self.num_players, dtype=bool)
            reach_probs = np.ones(self.num_players)
            
            # Start recursive CFR from pre-flop
            self._cfr_recursive(player_hands, history="", board=[], pot=0, bets=np.zeros(self.num_players), reach_probs=reach_probs, active_players=active_players, street=0, last_aggressor=1)

        logger.info("✅ Training complete. Finalizing strategies...")
        self._finalize_strategies()

    def _cfr_recursive(self, player_hands, history, board, pot, bets, reach_probs, active_players, street, last_aggressor) -> np.ndarray:
        """The core recursive function for Counter-Factual Regret Minimization for NLHE."""
        
        if self._is_terminal(active_players):
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players)

        if self._is_betting_round_over(history, bets, active_players, last_aggressor):
            return self._handle_new_street(player_hands, board, pot, bets, reach_probs, active_players, street)

        player = self._get_current_player(history, active_players)
        
        actions = self._get_available_actions(bets, pot)
        info_set = f"{self.num_players}p_{''.join(player_hands[player])}_{''.join(board)}_{history}"
        
        node = self.get_node(info_set, actions)
        strategy = node.get_strategy()
        
        action_utilities = np.zeros((node.num_actions, self.num_players))
        
        for i, action in enumerate(actions):
            new_history, new_pot, new_bets, new_active, new_aggressor = self._get_next_state(
                history, pot, bets, active_players, player, action, last_aggressor
            )
            
            new_reach_probs = reach_probs.copy()
            new_reach_probs[player] *= strategy[i]
            
            action_utilities[i] = self._cfr_recursive(
                player_hands, new_history, board, new_pot, new_bets, new_reach_probs, new_active, street, new_aggressor
            )

        node_utility = np.sum(strategy.reshape(-1, 1) * action_utilities, axis=0)
        
        player_action_utilities = action_utilities[:, player]
        player_node_utility = node_utility[player]
        regret = player_action_utilities - player_node_utility
        
        opponent_reach_prob = np.prod(np.delete(reach_probs, player))
        node.regret_sum += regret * opponent_reach_prob
        
        node.strategy_sum += reach_probs[player] * strategy

        return node_utility

    def _handle_new_street(self, player_hands, board, pot, bets, reach_probs, active_players, street):
        """Deals new cards and starts the next betting round."""
        new_street = street + 1
        
        # Add previous bets to the pot
        pot += np.sum(bets)
        new_bets = np.zeros(self.num_players)
        
        dealt_cards = [card for hand in player_hands for card in hand] + board
        remaining_deck = [card for card in self.deck if card not in dealt_cards]
        
        new_board = board[:]
        if new_street == 1: # Flop
            new_board.extend(remaining_deck[:3])
        elif new_street in [2, 3]: # Turn, River
            new_board.extend(remaining_deck[:1])

        # Post-flop action starts with the first active player from the SB
        return self._cfr_recursive(player_hands, "", new_board, pot, new_bets, reach_probs, active_players, new_street, last_aggressor=-1)

    def _is_terminal(self, active_players: np.ndarray) -> bool:
        return np.sum(active_players) <= 1

    def _is_betting_round_over(self, history, bets, active_players, last_aggressor) -> bool:
        # Simplified: round is over if all active players have bet the same amount
        active_bets = bets[active_players]
        if len(active_bets) > 0 and np.all(active_bets == active_bets[0]) and last_aggressor != -1:
             # And the action is closed (everyone has acted)
             # This is a simplification. A full implementation is more complex.
             if len(history) >= np.sum(active_players):
                 return True
        return False

    def _get_terminal_utility(self, player_hands, board, pot, bets, active_players) -> np.ndarray:
        """Calculates utility at a terminal node."""
        pot += np.sum(bets)
        payoffs = np.zeros(self.num_players)

        if np.sum(active_players) == 1:
            winner_idx = np.where(active_players)[0][0]
            payoffs[winner_idx] = pot
        else: # Showdown
            equities = self.equity_calculator.calculate_equities_gpu(
                [h for i, h in enumerate(player_hands) if active_players[i]],
                board,
                num_simulations=1000
            )
            
            active_indices = np.where(active_players)[0]
            for i, eq in enumerate(equities):
                payoffs[active_indices[i]] = eq * pot

        # Subtract what each player put in
        payoffs -= bets
        return payoffs

    def _get_current_player(self, history: str, active_players: np.ndarray) -> int:
        """Determines the current player to act."""
        # Simple rotation
        start_player = 0 # In reality, this depends on the street and button position
        player = (start_player + len(history)) % self.num_players
        while not active_players[player]:
            player = (player + 1) % self.num_players
        return player

    def _get_available_actions(self, bets, pot) -> List[str]:
        """Returns a simplified list of actions for NLHE."""
        # f=fold, c=call/check, r=raise pot
        actions = ['f', 'c']
        if pot > 0: # Can't raise if pot is 0 (should not happen after blinds)
            actions.append('r')
        return actions

    def _get_next_state(self, history, pot, bets, active_players, player, action, last_aggressor) -> Tuple:
        """Applies an action and returns the new game state."""
        new_active = active_players.copy()
        new_bets = bets.copy()
        new_pot = pot
        new_aggressor = last_aggressor

        if action == 'f':
            new_active[player] = False
        elif action == 'c':
            to_call = np.max(new_bets) - new_bets[player]
            new_bets[player] += to_call
        elif action == 'r':
            to_call = np.max(new_bets) - new_bets[player]
            raise_amount = new_pot + to_call # Pot-sized raise
            new_bets[player] += to_call + raise_amount
            new_aggressor = player
            
        return history + action, new_pot, new_bets, new_active, new_aggressor

    def _finalize_strategies(self):
        """Convert average strategies to the format expected by StrategyLookup."""
        logger.info(f"Finalizing {len(self.nodes)} strategies...")
        for info_set, node in self.nodes.items():
            avg_strategy = node.get_average_strategy()
            try:
                parts = info_set.split('_')
                street = "0" 
                hand_bucket = parts[1] if len(parts) > 1 else "default_hand"
                board_bucket = parts[2] if len(parts) > 2 else "default_board"

                self.strategy_lookup.add_strategy(
                    street, hand_bucket, board_bucket,
                    list(avg_strategy.keys()), avg_strategy
                )
            except Exception as e:
                logger.warning(f"Could not parse and save strategy for info_set '{info_set}': {e}")

        self.strategy_lookup.save_strategies()
        logger.info("Strategies saved successfully.")
