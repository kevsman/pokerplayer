"""
train_cfr.py
This script is responsible for the offline training of the poker bot using Counterfactual Regret Minimization (CFR).
It simulates games of poker where the bot plays against itself, learns from its regrets, and stores the resulting
strategies in a JSON file for the real-time bot to use.
"""
import logging
import random
import numpy as np
from collections import defaultdict

from hand_abstraction import HandAbstraction
from strategy_lookup import StrategyLookup
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    def __init__(self, num_players=6, big_blind=2, small_blind=1):
        self.num_players = num_players
        self.bb = big_blind
        self.sb = small_blind
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = EquityCalculator()
        self.abstraction = HandAbstraction(self.hand_evaluator, self.equity_calculator)
        self.strategy_lookup = StrategyLookup()
        self.nodes = {}

    def get_node(self, info_set, actions):
        if info_set not in self.nodes:
            self.nodes[info_set] = CFRNode(len(actions), actions)
        return self.nodes[info_set]

    def get_available_actions(self, current_bet, player_bet):
        actions = ['fold']
        if current_bet == player_bet:
            actions.append('check')
        else:
            actions.append('call')
        actions.append('raise')
        return actions

    def cfr(self, cards, history, pot, bets, active_mask, street, current_player, reach_probabilities):
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
            
            evals = {i: self.hand_evaluator.evaluate_hand(h, community_cards) for i, h in player_hands.items()}
            
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

        actions = self.get_available_actions(max(bets), bets[current_player])
        node = self.get_node(info_set, actions)
        strategy = node.get_strategy()

        action_utils = np.zeros((self.num_players, len(actions)))

        for i, action in enumerate(actions):
            next_reach = reach_probabilities.copy()
            next_reach[current_player] *= strategy[i]
            
            new_history = history + action[0]
            new_bets = bets.copy()
            new_pot = pot
            new_active_mask = active_mask.copy()

            if action == 'fold':
                new_active_mask[current_player] = False
                action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach)
            
            elif action == 'call':
                amount_to_call = max(bets) - new_bets[current_player]
                new_bets[current_player] += amount_to_call
                new_pot += amount_to_call
                # Check if betting round is over
                if all(b == new_bets[current_player] for i, b in enumerate(new_bets) if new_active_mask[i]):
                    action_utils[:, i] = self.cfr(cards, new_history + '|', new_pot, new_bets, new_active_mask, street + 1, 0, next_reach)
                else:
                    action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach)

            elif action == 'check':
                 action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach)

            elif action == 'raise':
                # Simplified raise sizing
                raise_amount = new_pot 
                new_bets[current_player] += raise_amount
                new_pot += raise_amount
                action_utils[:, i] = self.cfr(cards, new_history, new_pot, new_bets, new_active_mask, street, next_player, next_reach)

        # Calculate node values and update regrets
        node_util_for_player = np.sum(strategy * action_utils[current_player])
        regret = action_utils[current_player] - node_util_for_player
        
        reach_prob = reach_probabilities[current_player]
        cfr_reach = np.prod(np.delete(reach_probabilities, current_player))

        node.regret_sum += cfr_reach * regret
        node.strategy_sum += reach_prob * strategy

        return np.sum(strategy.reshape(-1, 1) * action_utils, axis=0)


    def train(self, iterations):
        logger.info(f"Starting CFR training for {iterations} iterations on a {self.num_players}-player table.")
        
        for i in range(iterations):
            if i > 0 and i % 1000 == 0:
                logger.info(f"Iteration {i}/{iterations}")

            deck = self.equity_calculator._generate_deck()
            random.shuffle(deck)
            
            player_cards = [deck[j*2:j*2+2] for j in range(self.num_players)]
            
            # Initial game state
            pot = self.sb + self.bb
            bets = np.zeros(self.num_players)
            bets[1] = self.sb # Player 1 is SB
            bets[2] = self.bb # Player 2 is BB (UTG is player 3)
            active_mask = np.ones(self.num_players, dtype=bool)
            reach_probabilities = np.ones(self.num_players)
            
            self.cfr(cards=deck, history="", pot=pot, bets=bets, active_mask=active_mask, street=0, current_player=3 % self.num_players, reach_probabilities=reach_probabilities)

        logger.info("Training complete. Converting nodes to strategy format...")
        for info_set, node in self.nodes.items():
            try:
                street, hand_bucket, board_bucket, history_str = info_set.split('|', 3)
                actions = node.actions
                avg_strategy = node.get_average_strategy()
                strategy_dict = {act: p for act, p in zip(actions, avg_strategy)}
                self.strategy_lookup.update_strategy(street, hand_bucket, board_bucket, list(strategy_dict.keys()), strategy_dict)
            except ValueError:
                logger.warning(f"Could not parse info_set: {info_set}")
                continue

        logger.info("Saving strategies...")
        self.strategy_lookup.save_strategies()
        logger.info(f"Strategies saved to {self.strategy_lookup.filepath}")



if __name__ == "__main__":
    trainer = CFRTrainer(num_players=6)
    trainer.train(iterations=50000)
