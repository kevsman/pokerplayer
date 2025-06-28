"""
GPU-accelerated CFR trainer for poker bot.
This version implements a recursive CFR algorithm for No-Limit Hold'em,
supporting up to 6 players and configurable blinds. It's based on the principles
from the article: https://medium.com/@olegostroumov/worlds-first-poker-solver-6b1dbe80d0ee
but adapted for the more complex game of No-Limit Hold'em.
"""
import numpy as np
import logging
import time
from typing import List, Dict, Tuple
import random

# --- Mock Objects for Safe Execution ---
class MockLogger:
    def info(self, msg):
        pass
    def debug(self, msg):
        pass
    def error(self, msg):
        pass
    def warning(self, msg):
        pass

logger = MockLogger()
GPU_AVAILABLE = False
# --- End Mock Objects ---

# Disable logging for this module to prevent potential recursion issues from complex string representations.
logging.getLogger(__name__).setLevel(logging.CRITICAL + 1)

from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from strategy_lookup import StrategyLookup

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
    """A GPU-accelerated CFR trainer for No-Limit Hold'em."""
    def __init__(self, use_gpu=True, num_players=6, small_blind=0.02, big_blind=0.04, initial_stack=4.0):
        self.num_players = num_players
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.initial_stack = self.big_blind * 100  # Each player starts with 100 BB
        self.num_simulations = 1000
        
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = GPUEquityCalculator(use_gpu=self.use_gpu)
        self.strategy_lookup = StrategyLookup()
        
        self.nodes: Dict[str, CFRNode] = {}
        self.deck = self.equity_calculator.all_cards[:]
        
        # self._setup_logging() # Call setup before logging
        logger.info(f"GPUCFRTrainer for NLHE initialized. Players: {num_players}, Blinds: {small_blind}/{big_blind}, Stacks: {self.initial_stack}, GPU: {self.use_gpu}")
        self.hand_counter = 0
        self.recursion_depth = 0

    def _ascii_safe_str(self, obj: any) -> str:
        """Converts an object to its string representation and replaces unicode card suits with ASCII."""
        s = str(obj)
        s = s.replace('♥', 'h').replace('♦', 'd').replace('♣', 'c').replace('♠', 's')
        return s

    def _setup_logging(self):
        """Configure file and console logging."""
        # This function is now deprecated. BasicConfig is used instead.
        pass

    def get_node(self, info_set: str, actions: List[str]) -> CFRNode:
        """Retrieve or create a CFRNode for a given information set."""
        if info_set not in self.nodes:
            self.nodes[info_set] = CFRNode(len(actions), actions)
        return self.nodes[info_set]

    def _get_strategy(self, info_set: str, actions: List[str]) -> np.ndarray:
        """Get the current strategy profile for an information set."""
        node = self.get_node(info_set, actions)
        return node.get_strategy()

    def _initialize_deck(self) -> List[str]:
        """Returns a copy of the master deck for a new hand."""
        return self.deck[:]

    def _post_blinds(self) -> Tuple[float, np.ndarray, np.ndarray]:
        """This method is now stateful and requires player_stacks."""
        raise NotImplementedError("Call the version of _post_blinds that takes player_stacks.")

    def _post_blinds(self, player_stacks: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
        """Posts blinds, adjusting player stacks, and returns initial pot, bets, and active players."""
        pot = 0.0
        bets = np.zeros(self.num_players)
        active_players = np.ones(self.num_players, dtype=bool)

        # Small blind (player 0)
        sb_amount = min(self.small_blind, player_stacks[0])
        bets[0] = sb_amount
        player_stacks[0] -= sb_amount

        # Big blind (player 1)
        bb_amount = min(self.big_blind, player_stacks[1])
        bets[1] = bb_amount
        player_stacks[1] -= bb_amount

        return pot, bets, active_players

    def train_like_fixed_cfr(self, iterations: int):
        """Run the CFR training for NLHE."""
        logger.info(f"🚀 Starting NLHE CFR training for {iterations} iterations...")

        for i in range(iterations):
            self.hand_counter += 1
            logger.info(f"--- Iteration {i + 1}/{iterations} (Hand #{self.hand_counter}) ---")
            
            deck = self._initialize_deck()
            random.shuffle(deck)
            player_hands = [deck[j*2:j*2+2] for j in range(self.num_players)]

            # Initialize stacks and post blinds
            player_stacks = np.full(self.num_players, self.initial_stack, dtype=float)
            pot, bets, active_players = self._post_blinds(player_stacks)
            
            reach_probs = np.ones(self.num_players)
            
            # Start recursive CFR from pre-flop.
            self._cfr_recursive(player_hands, history="", board=[], pot=pot, bets=bets, reach_probs=reach_probs, active_players=active_players, player_stacks=player_stacks, street=0, num_actions_this_street=0, recursion_depth=0)

        logger.info("✅ Training complete. Finalizing strategies...")
        self._finalize_strategies()
        logging.shutdown() # Ensure all logs are flushed and handlers closed.

    def _cfr_recursive(self, player_hands, history, board, pot, bets, reach_probs, active_players, player_stacks, street, num_actions_this_street, recursion_depth):
        """The core recursive function for Counter-Factual Regret Minimization for NLHE."""
        self.recursion_depth = recursion_depth
        logger.debug(f"ENTER _cfr_recursive: depth={recursion_depth}, street={street}, hist='{history}', board={board}, can_act={self._can_any_player_act(active_players, player_stacks)}")

        if recursion_depth > 100: # A hard limit to prevent true infinite recursion
            logger.error(f"[HAND #{self.hand_counter}] RECURSION DEPTH LIMIT EXCEEDED! Bailing out.")
            logger.error(f"State: street={street}, hist='{history}', board={board}, pot={pot}, bets={bets}, stacks={player_stacks}, active={active_players}")
            return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)

        # If no player can act (e.g., everyone is all-in), fast-forward to showdown.
        if not self._can_any_player_act(active_players, player_stacks):
            logger.debug("DETECTED: No player can act. Fast-forwarding to showdown.")
            
            # Add current bets to the pot before dealing further.
            pot += np.sum(bets)
            bets = np.zeros(self.num_players)

            # Deal remaining cards to complete the board
            final_board = board[:]
            num_cards_to_deal = 5 - len(final_board)
            
            if num_cards_to_deal > 0:
                dealt_cards = [card for hand in player_hands for card in hand] + final_board
                flat_dealt_cards = []
                for item in dealt_cards:
                    if isinstance(item, list):
                        flat_dealt_cards.extend(item)
                    else:
                        flat_dealt_cards.append(item)
                
                remaining_deck = [card for card in self.deck if card not in flat_dealt_cards]
                random.shuffle(remaining_deck)
                final_board.extend(remaining_deck[:num_cards_to_deal])
                logger.debug(f"Dealt remaining {num_cards_to_deal} cards. Final board: {final_board}")

            return self._get_terminal_utility(player_hands, final_board, pot, bets, active_players, player_stacks)

        is_over = self._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
        
        # Override if no player can act (e.g., everyone is all-in)
        if not self._can_any_player_act(active_players, player_stacks):
            logger.debug("DETECTED: No player can act. Forcing is_over=True.")
            is_over = True

        if is_over:
            if street == 3:  # River betting round is over, go to showdown
                logger.debug(f"END OF RECURSION: street is 3, calling _get_terminal_utility. depth={recursion_depth}")
                return self._get_terminal_utility(player_hands, board, pot, bets, active_players, player_stacks)
            else:
                logger.debug(f"RECURSING FURTHER: street is {street}, calling _handle_new_street. depth={recursion_depth}")
                return self._handle_new_street(player_hands, board, pot, bets, reach_probs, active_players, player_stacks, street, recursion_depth)

        # Determine the current player to act
        player = self._get_current_player(history, active_players, street, pot, num_actions_this_street, player_stacks)
        
        if player == -1: # All remaining players are all-in
            logger.debug("All remaining players are all-in, but round not over. Handling new street.")
            return self._handle_new_street(player_hands, board, pot, bets, reach_probs, active_players, player_stacks, street, recursion_depth)

        actions = self._get_available_actions(player, bets, player_stacks)
        
        # Make the info_set more specific by including a bucketed stack-to-pot ratio and the actions
        current_pot_size = pot + np.sum(bets)
        player_stack = player_stacks[player]
        spr = player_stack / current_pot_size if current_pot_size > 0 else 100.0 # Use a large SPR if pot is 0
        spr_bucket = round(spr * 4) / 4.0 # Bucket SPR to nearest 0.25
        
        # Add actions to info_set key to prevent mismatches. Sort for a canonical representation.
        actions_str = "".join(sorted(actions))

        info_set = f"{self.num_players}p_{''.join(player_hands[player])}_{''.join(board)}_{history}_{''.join(map(lambda x: f'{x:.2f}', bets))}_{spr_bucket}_{actions_str}"
        logger.debug(f"Player {player}: InfoSet='{info_set}'")
        
        # Get strategy from the CFR node
        strategy = self._get_strategy(info_set, actions)
        logger.debug(f"Player {player}: Strategy for InfoSet: {list(zip(actions, strategy))}")

        # The return value of _cfr_recursive is a numpy array of utilities for each player.
        node_utility_vector = np.zeros(self.num_players)
        cf_values_for_player = np.zeros(len(actions))

        # Explore each action
        for i, action in enumerate(actions):
            logger.debug(self._ascii_safe_str(f"  Player {player} exploring action '{action}'"))

            # Create a new history string for the next state
            new_history = f"{history}{action}"
            new_bets = bets.copy()
            new_pot = pot
            new_active_players = active_players.copy()
            new_stacks = player_stacks.copy()
            new_num_actions_this_street = num_actions_this_street + 1

            if action == 'f':
                new_active_players[player] = False
            elif action == 'k': # Check
                pass # No change in bets
            elif action == 'c': # Call
                max_bet = np.max(new_bets)
                amount_to_add = max_bet - new_bets[player]
                amount_to_add = min(amount_to_add, new_stacks[player]) # All-in call
                new_bets[player] += amount_to_add
                new_stacks[player] -= amount_to_add
            elif action == 'r':
                max_bet = np.max(new_bets)
                to_call = max_bet - new_bets[player]
                
                current_pot_size = pot + np.sum(bets)
                # Pot-sized raise: bet the size of the pot after calling
                raise_amount = current_pot_size + to_call
                
                new_total_bet = new_bets[player] + to_call + raise_amount
               
                # Amount to add from stack is the difference from current bet
                amount_to_add = new_total_bet - new_bets[player]
                
                # Cap by stack
                amount_to_add = min(amount_to_add, new_stacks[player])

                # A raise must be at least twice the previous bet/raise, but here we simplify
                # and just ensure it's a valid increase. If not, it becomes an all-in.
                if amount_to_add > to_call:
                    new_bets[player] += amount_to_add
                    new_stacks[player] -= amount_to_add
                else: # Not enough to raise, so just go all-in
                    amount_to_add = new_stacks[player]
                    new_bets[player] += amount_to_add
                    new_stacks[player] -= amount_to_add

            new_reach_probs = reach_probs.copy()
            # Update reach probabilities for the next state
            new_reach_probs[player] *= strategy[i]

            logger.debug(self._ascii_safe_str(f"  Player {player} exploring action '{action}' with prob {strategy[i]:.4f}"))


            # Recursively call _cfr_recursive for the next state
            utility_vector = self._cfr_recursive(
                player_hands,
                new_history,
                board,
                new_pot,
                new_bets,
                new_reach_probs,
                new_active_players,
                new_stacks,
                street,
                new_num_actions_this_street,
                recursion_depth + 1
            )

            # Update the node utility vector
            node_utility_vector += strategy[i] * utility_vector
            cf_values_for_player[i] = utility_vector[player]


        # After iterating through all actions, calculate regret and update strategy
        # Node utility for the current player
        node_utility_for_player = np.sum(strategy * cf_values_for_player)
        
        # Update regrets and strategy sum
        node = self.get_node(info_set, actions)
        regrets = cf_values_for_player - node_utility_for_player
        node.regret_sum += regrets
        node.strategy_sum += reach_probs[player] * strategy

        return node_utility_vector


    def _handle_new_street(self, player_hands, board, pot, bets, reach_probs, active_players, player_stacks, street, recursion_depth):
        """Deals new cards and starts the next betting round."""
        new_street = street + 1
        
        logger.debug(f"ENTER _handle_new_street: current_street={street}, new_street={new_street}, depth={recursion_depth}")
        
        # Add previous bets to the pot
        pot += np.sum(bets)
        new_bets = np.zeros(self.num_players)
        
        dealt_cards = [card for hand in player_hands for card in hand] + board
        
        # Ensure dealt_cards are flattened if they are lists of lists
        flat_dealt_cards = []
        for item in dealt_cards:
            if isinstance(item, list):
                flat_dealt_cards.extend(item)
            else:
                flat_dealt_cards.append(item)

        remaining_deck = [card for card in self.deck if card not in flat_dealt_cards]
        random.shuffle(remaining_deck)

        new_board = board[:]
        if new_street == 1: # Flop
            new_board.extend(remaining_deck[:3])
        elif new_street in [2, 3]: # Turn, River
            new_board.extend(remaining_deck[:1])

        logger.debug(self._ascii_safe_str(f"New Board: {new_board}, New Pot: {pot:.2f}"))

        # Post-flop action starts with the first active player from the SB
        return self._cfr_recursive(player_hands, "", new_board, pot, new_bets, reach_probs, active_players, player_stacks, new_street, num_actions_this_street=0, recursion_depth=recursion_depth + 1)

    def _is_terminal(self, active_players: np.ndarray) -> bool:
        return np.sum(active_players) <= 1

    def _is_betting_round_over(self, history: str, bets: np.ndarray, active_players: np.ndarray, street: int, num_actions_this_street: int, player_stacks: np.ndarray) -> bool:
        """Checks if the betting round is over with a more robust logic."""
        num_active = np.sum(active_players)
        if num_active <= 1:
            logger.debug(f"Betting round over: {num_active} active players.")
            return True

        # Players who are still in the hand and have chips to act
        can_act_mask = active_players & (player_stacks > 0)
        num_can_act = np.sum(can_act_mask)

        # If 0 or 1 players can act, the betting round is over.
        if num_can_act <= 1:
            logger.debug(f"Betting round over: {num_can_act} players can act.")
            return True

        # Check if all players who can act have contributed the same amount.
        bets_of_actors = bets[can_act_mask]
        bets_are_equal = len(np.unique(bets_of_actors)) == 1
        
        # The first action on any street cannot end the round unless it's an all-in.
        if num_actions_this_street == 0:
            return False

        if bets_are_equal:
            # Pre-flop: The round is over if everyone has acted, or if the BB had the option and checked.
            if street == 0:
                # The round can't be over until at least `num_active` players have acted (limpers + blinds)
                # or the big blind checks/raises on their option.
                is_bb_option_case = (bets[1] == self.big_blind and np.max(bets) == self.big_blind)
                if is_bb_option_case:
                    # If it's the BB's option, the round ends if they check (history ends in 'k')
                    # or if everyone else folded to the BB.
                    if history.endswith('k') and num_actions_this_street >= num_active:
                         return True
                    return False # BB must act
               
                # Standard case: everyone called or folded to the initial bet.
                if num_actions_this_street >= num_active:
                    return True

            # Post-flop: The round is over if everyone has checked or called a bet.
            else:
                # If bets are equal (e.g., all zero from checks), and everyone has had a turn, the round is over.
                if num_actions_this_street >= num_can_act:
                    logger.debug(f"Betting round over: Post-flop, {num_actions_this_street} actions, {num_can_act} can act, bets equal.")
                    return True
        
        logger.debug(f"Betting round continues: street={street}, num_actions={num_actions_this_street}, num_can_act={num_can_act}, bets_equal={bets_are_equal}, hist='{history}'")
        return False

    def _get_terminal_utility(self, player_hands, board, pot, bets, active_players, player_stacks) -> np.ndarray:
        """Calculates the utility at a terminal node (showdown or last man standing)."""
        
        logger.debug(f"--- Terminal Node Reached ---")
        logger.debug(self._ascii_safe_str(f"Board: {board}, Pot: {pot}, Bets sum: {np.sum(bets)}, Active: {active_players}"))

        # Investment is the total amount each player put into the pot during the hand.
        investment = self.initial_stack - player_stacks
        payoffs = np.zeros(self.num_players)
        total_pot = pot + np.sum(bets)

        logger.debug(self._ascii_safe_str(f"TERMINAL. Active: {active_players}, Pot: {total_pot:.2f}, Board: {board}"))

        if np.sum(active_players) == 1:
            winner_idx = np.where(active_players)[0][0]
            winnings = np.zeros(self.num_players)
            winnings[winner_idx] = total_pot
            payoffs = winnings - investment
            logger.debug(f"Winner by fold: Player {winner_idx}. Payoffs: {payoffs}")
            # The sum of payoffs should be zero.
            if not np.isclose(np.sum(payoffs), 0):
                logger.warning(f"Payoffs do not sum to zero in non-showdown. Sum: {np.sum(payoffs)}")
            return payoffs

        # Showdown
        active_player_indices = np.where(active_players)[0]
        hands_to_evaluate = [player_hands[i] for i in active_player_indices]
        
        logger.debug(self._ascii_safe_str(f"Showdown. Board: {board}, Hands: {hands_to_evaluate}, Players: {active_player_indices}"))

        known_cards = [card for hand in hands_to_evaluate for card in hand] + board
        
        # Ensure dealt_cards are flattened if they are lists of lists
        flat_dealt_cards = []
        for item in known_cards:
            if isinstance(item, list):
                flat_dealt_cards.extend(item)
            else:
                flat_dealt_cards.append(item)

        remaining_deck = [card for card in self.deck if card not in flat_dealt_cards]

        wins = np.zeros(len(active_player_indices))
        
        if len(board) < 5:
            for _ in range(self.num_simulations):
                random.shuffle(remaining_deck)
                
                num_cards_to_draw = 5 - len(board)
                board_completion = remaining_deck[:num_cards_to_draw]
                full_board = board + board_completion
                
                scores = [self.hand_evaluator.evaluate_hand(hand, full_board)['rank_value'] for hand in hands_to_evaluate]
                best_score = max(scores)
                winners = [i for i, score in enumerate(scores) if score == best_score]
                for winner_idx in winners:
                    wins[winner_idx] += 1 / len(winners)
            
            equities = wins / self.num_simulations
        else: # board is complete
            scores = [self.hand_evaluator.evaluate_hand(hand, board)['rank_value'] for hand in hands_to_evaluate]
            best_score = max(scores)
            winners = [i for i, score in enumerate(scores) if score == best_score]
            equities = np.zeros(len(active_player_indices))
            for winner_idx in winners:
                equities[winner_idx] = 1 / len(winners)

        # Simplified payoff distribution - does not handle side pots.
        # This is a known simplification where all players contest the main pot.
        winnings = np.zeros(self.num_players)
        for i, player_idx in enumerate(active_player_indices):
            winnings[player_idx] = equities[i] * total_pot

        payoffs = winnings - investment
        logger.debug(f"Showdown equities shape: {equities.shape}, Winnings sum: {np.sum(winnings)}, Investment sum: {np.sum(investment)}, Payoffs sum: {np.sum(payoffs)}")
        
        # The sum of payoffs must be zero for a zero-sum game.
        if not np.isclose(np.sum(payoffs), 0.0, atol=1e-6):
             logger.warning(f"Payoffs do not sum to zero in showdown. Sum: {np.sum(payoffs)}, Winnings: {winnings}, Investment: {investment}")

        return payoffs

    def _can_any_player_act(self, active_players: np.ndarray, player_stacks: np.ndarray) -> bool:
        """Checks if any player in the hand has chips left to act."""
        return np.any(active_players & (player_stacks > 0))

    def _get_current_player(self, history: str, active_players: np.ndarray, street: int, pot: float, num_actions_this_street: int, player_stacks: np.ndarray) -> int:
        """Determines the current player to act, skipping folded and all-in players."""
        if street == 0:  # Pre-flop
            # Action starts UTG (player 2 in a 6-max game, left of BB)
            start_player_initial = 2 % self.num_players
        else:  # Post-flop
            # Action starts with the first active player from the SB (player 0)
            start_player_initial = 0

        # Find the first active, non-all-in player to start the round's action
        player = start_player_initial
        start_search = start_player_initial
        while not active_players[player] or player_stacks[player] <= 0:
            player = (player + 1) % self.num_players
            if player == start_search:
                logger.debug("Get current player: No player can act.")
                return -1 # No one can act

        # Advance the turn `num_actions_this_street` times, properly skipping inactive players.
        for _ in range(num_actions_this_street):
            player = (player + 1) % self.num_players
            search_start = player
            while not active_players[player] or player_stacks[player] <= 0:
                player = (player + 1) % self.num_players
                if player == search_start: # Cycled through all players
                    logger.debug("Get current player: No player can act after advancing turn.")
                    return -1 # No player can act

        logger.debug(f"Current player is {player}")
        return player

    def _get_available_actions(self, player: int, bets: np.ndarray, player_stacks: np.ndarray) -> List[str]:
        """Returns a simplified list of actions for NLHE, aware of stack sizes."""
        actions = []
        stack = player_stacks[player]
        
        if stack <= 0:
            logger.debug(f"Player {player} has no actions, stack is {stack}.")
            return []

        max_bet = np.max(bets)
        player_bet = bets[player]

        can_raise = False
        to_call = max_bet - player_bet
        if stack > to_call:
            can_raise = True

        if max_bet > player_bet:
            actions.append('f')
            actions.append('c')
        else:
            actions.append('k')
        
        if can_raise:
            actions.append('r')
            
        logger.debug(f"Player {player} available actions: {actions}. Stack: {stack}, Bet: {player_bet}, Max Bet: {max_bet}")
        return actions

    def _finalize_strategies(self):
        """Convert average strategies to the format expected by StrategyLookup and save them."""
        logger.info("Saving final strategies...")
        final_strategies = self.get_final_strategy()
        self.strategy_lookup.strategies = final_strategies
        # Assuming strategy_lookup has a method to save the strategies to its file.
        # This part might need adjustment based on the actual implementation of StrategyLookup.
        if hasattr(self.strategy_lookup, 'save_strategies'):
             self.strategy_lookup.save_strategies()
             logger.info(f"Saved {len(final_strategies)} information sets.")
        else:
             logger.warning("StrategyLookup does not have a `save_strategies` method. Final strategy not saved.")

    def get_final_strategy(self) -> Dict[str, Dict[str, float]]:
        """Returns the computed strategy."""
        final_strategy = {}
        for info_set, node in self.nodes.items():
            final_strategy[info_set] = node.get_average_strategy()
        return final_strategy
