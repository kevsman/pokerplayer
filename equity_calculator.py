import random
from itertools import combinations
from hand_evaluator import HandEvaluator
import logging

logger = logging.getLogger(__name__)

class EquityCalculator:
    SUIT_MAP = {
        's': '♠', 'h': '♥', 'd': '♦', 'c': '♣',
        'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣',
        '♠': '♠', '♥': '♥', '♦': '♦', '♣': '♣'  # Idempotent for already symbol-suited cards
    }

    def __init__(self):
        self.hand_evaluator = HandEvaluator()
        self.all_cards = self._generate_deck()
    
    def _generate_deck(self):
        """Generate a standard 52-card deck"""
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠', '♥', '♦', '♣']
        return [rank + suit for rank in ranks for suit in suits]
    
    def _normalize_card(self, card_str):
        if not isinstance(card_str, str) or len(card_str) < 2:
            return None 
        
        rank = card_str[:-1] 
        suit_char = card_str[-1]

        # Ensure rank is uppercase if it's a letter, e.g. 'a' for Ace -> 'A'
        # Common ranks like 'T', 'J', 'Q', 'K', 'A' are typically uppercase.
        # '10' is a two-character rank.
        if not rank == '10' and len(rank) == 1: # Single character ranks (A, K, Q, J, T, 9, 8...)
            rank = rank.upper()
        
        normalized_suit = self.SUIT_MAP.get(suit_char)
        if not normalized_suit:
            return None # Invalid suit character
        
        return rank + normalized_suit

    def _normalize_card_list(self, card_list_input):
        if not card_list_input: # Handles None or empty list
            return [] 
        
        normalized_cards = []
        for card_str in card_list_input:
            norm_card = self._normalize_card(card_str)
            if norm_card:
                normalized_cards.append(norm_card)
            else:
                # Invalid card found in the input list, normalization for the whole list fails
                return None 
        return normalized_cards

    def _get_unknown_cards(self, known_cards):
        """Get cards that are not in the known cards list"""
        return [card for card in self.all_cards if card not in known_cards]
    
    def calculate_equity_monte_carlo(self, hole_cards_str_list, community_cards_str_list, opponent_range_str_list, num_simulations):
        # Expects normalized card strings, e.g., [['Ah', 'Qh']], ['Kh', 'Jd', '2c']
        logger.debug(
            f"Enter calculate_equity_monte_carlo. Hole Cards: {hole_cards_str_list}, "
            f"Community Cards: {community_cards_str_list}, Opponent Range: {opponent_range_str_list}, "
            f"Simulations: {num_simulations}"
        )

        if not hole_cards_str_list or not hole_cards_str_list[0]:
            logger.error("Player hole cards are missing. Cannot calculate equity.")
            return 0.0, 0.0, 0.0 # Win, Tie, Equity

        player_wins = 0
        ties = 0
        total_simulations_count = 0 # Counts successful simulations

        # Assuming hole_cards_str_list contains one list of cards for the player
        raw_player_cards_input = hole_cards_str_list[0]
        
        player_hole_cards_str_list_for_conversion = []
        if isinstance(raw_player_cards_input, str):
            # If "Ah", treat as a single card string in a list
            player_hole_cards_str_list_for_conversion = [raw_player_cards_input]
        elif isinstance(raw_player_cards_input, list):
            # If [\'Ah\', \'Kh\'] or [\'Ah\'], it\'s already in the correct list format
            player_hole_cards_str_list_for_conversion = raw_player_cards_input
        else:
            logger.error(f"Unexpected type for player hole cards input: {type(raw_player_cards_input)}. Value: {raw_player_cards_input}")
            # Fallback to empty list, which will lead to an error return shortly
            player_hole_cards_str_list_for_conversion = []

        try:
            player_hole_cards_obj = [self.hand_evaluator._convert_card_to_value(c) for c in player_hole_cards_str_list_for_conversion]
            community_cards_obj = [self.hand_evaluator._convert_card_to_value(c) for c in community_cards_str_list]
            
            player_hole_cards_obj = [c for c in player_hole_cards_obj if c is not None]
            community_cards_obj = [c for c in community_cards_obj if c is not None]

            # Critical check: if player\'s hole cards couldn\'t be converted, equity calculation is not meaningful.
            if len(player_hole_cards_obj) != len(player_hole_cards_str_list_for_conversion):
                logger.error(f"Failed to convert all player hole cards. Input: {player_hole_cards_str_list_for_conversion} -> Converted: {player_hole_cards_obj}")
                return 0.0, 0.0, 0.0
            
            # Log if community cards failed conversion, but proceed if player cards are okay.
            if len(community_cards_obj) != len(community_cards_str_list):
                logger.warning(f"Failed to convert some community cards. Input: {community_cards_str_list} -> Converted: {community_cards_obj}")

        except Exception as e:
            logger.error(f"Error during card conversion: {e}", exc_info=True)
            return 0.0, 0.0, 0.0

        deck = self._generate_deck() # Changed from self.hand_evaluator.create_deck()
        deck = [c for c in deck if c not in player_hole_cards_obj and c not in community_cards_obj]

        for i in range(num_simulations):
            current_deck = list(deck) # Make a copy for this simulation
            
            try:
                # Determine how many more board cards are needed
                num_board_cards_needed = 5 - len(community_cards_obj)
                
                # Deal opponent hand (assuming one opponent for now, using 'random' range)
                # This part needs to be robust for different ranges. For 'random', deal 2 cards.
                if len(current_deck) < 2 + num_board_cards_needed:
                    logger.warning(f"Not enough cards in deck ({len(current_deck)}) to deal opponent hand and remaining board. Skipping simulation {i}.")
                    continue

                opponent_hole_cards_sim_obj = self.hand_evaluator.deal_random_cards(current_deck, 2)
                
                # Deal remaining board cards
                additional_board_cards_obj = []
                if num_board_cards_needed > 0:
                    if len(current_deck) < num_board_cards_needed:
                        logger.warning(f"Not enough cards in deck ({len(current_deck)}) to deal remaining board cards. Skipping simulation {i}.")
                        continue
                    additional_board_cards_obj = self.hand_evaluator.deal_random_cards(current_deck, num_board_cards_needed)
                
                current_board_sim_obj = community_cards_obj + additional_board_cards_obj

                # Log cards before evaluation
                # logger.debug(f"Sim {i}: Player: {player_hole_cards_str}, Opponent: {self.hand_evaluator.cards_to_strings(opponent_hole_cards_sim_obj)}, Board: {self.hand_evaluator.cards_to_strings(current_board_sim_obj)}")

                player_eval = self.hand_evaluator.evaluate_hand(player_hole_cards_obj, current_board_sim_obj)
                opponent_eval = self.hand_evaluator.evaluate_hand(opponent_hole_cards_sim_obj, current_board_sim_obj)

                # logger.debug(f"Sim {i}: Player Eval: {player_eval}, Opponent Eval: {opponent_eval}")

                comparison_result = self._compare_hands(player_eval, opponent_eval)
                if comparison_result > 0:
                    player_wins += 1
                elif comparison_result == 0:
                    ties += 1
                # else: loss, no increment needed for losses count here

                total_simulations_count += 1 # Increment for a successful simulation run

            except Exception as e:
                logger.error(f"Error during simulation run #{i}: {e}", exc_info=True)
                # Continue to next simulation attempt
                continue
        
        if total_simulations_count == 0:
            logger.warning(
                f"Total successful simulations was 0 for hole_cards: {player_hole_cards_str_list_for_conversion}, "
                f"community_cards: {community_cards_str_list}, opponent_range: {opponent_range_str_list}. "
                "This might indicate an issue with deck generation or simulation logic if cards were valid."
            )
            return 0.0, 0.0, 0.0 
        
        win_probability = player_wins / total_simulations_count
        tie_probability = ties / total_simulations_count
        
        # Equity is typically win_prob + (tie_prob / 2) if splitting pot on tie.
        # Or, more generally, related to pot share. For now, let's use a simple definition.
        equity = win_probability # Simplified, often (win_prob + tie_prob / num_opponents_sharing_tie)

        logger.info(
            f"Equity calculation complete for {player_hole_cards_str_list_for_conversion} vs random. "
            f"Win: {win_probability:.2f}%, Tie: {tie_probability:.2f}%, Equity: {equity:.2f}% "
            f"({total_simulations_count} simulations)"
        )
        return win_probability, tie_probability, equity
    
    def _compare_hands(self, hand1_eval, hand2_eval):
        """
        Compare two hand evaluations (dictionaries from evaluate_hand)
        Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie
        """
        # Ensure both evaluations are valid dictionaries with 'rank_value'
        if not isinstance(hand1_eval, dict) or 'rank_value' not in hand1_eval:
            logger.error(f"Invalid hand1_eval: {hand1_eval}")
            # Assuming if one hand is invalid, it cannot be compared meaningfully or loses by default
            # Depending on rules, this might need adjustment. If hand2 is also invalid, it's a tie of invalids.
            return -1 if isinstance(hand2_eval, dict) and 'rank_value' in hand2_eval else 0
        
        if not isinstance(hand2_eval, dict) or 'rank_value' not in hand2_eval:
            logger.error(f"Invalid hand2_eval: {hand2_eval}")
            return 1 # hand1 wins if hand2 is invalid and hand1 is valid

        hand1_rank_value = hand1_eval['rank_value']
        hand2_rank_value = hand2_eval['rank_value']

        if hand1_rank_value > hand2_rank_value:  # hand1 has better rank
            return 1
        elif hand1_rank_value < hand2_rank_value:  # hand2 has better rank
            return -1
        else:  # Same rank, compare tie breakers
            # Ensure 'tie_breakers' exist and are comparable
            hand1_tie_breakers = hand1_eval.get('tie_breakers')
            hand2_tie_breakers = hand2_eval.get('tie_breakers')

            # If tie_breakers are missing or not lists, this comparison might be problematic
            # HandEvaluator._compare_tie_breakers should handle this
            return self.hand_evaluator._compare_tie_breakers(hand1_tie_breakers, hand2_tie_breakers)
    
    def estimate_outs(self, hero_cards, community_cards):
        """
        Estimate the number of outs (cards that improve the hand)
        """
        # Normalize inputs
        hero_cards_norm = self._normalize_card_list(hero_cards)
        community_cards_norm = self._normalize_card_list(community_cards)

        if hero_cards_norm is None or len(hero_cards_norm) != 2:
            return 0 
        if community_cards and community_cards_norm is None: # Normalization failed for non-empty community cards
            return 0
        if community_cards_norm is None: # Ensure it's a list for processing
            community_cards_norm = []

        if len(community_cards_norm) < 3:
            return 0  # Can't estimate outs pre-flop or with too few community cards
            
        current_hand = self.hand_evaluator.calculate_best_hand(hero_cards_norm, community_cards_norm)
        known_cards = hero_cards_norm + community_cards_norm
        unknown_cards = self._get_unknown_cards(known_cards)
        
        outs = 0
        cards_to_come = 5 - len(community_cards_norm)
        
        if cards_to_come == 0:
            return 0
            
        # Test each unknown card to see if it improves our hand
        for card in unknown_cards:
            test_community = community_cards_norm + [card]
            if len(test_community) <= 5:
                test_hand_eval = self.hand_evaluator.calculate_best_hand(hero_cards_norm, test_community)
                # current_hand is already an eval dictionary
                if self._compare_hands(test_hand_eval, current_hand) > 0:
                    outs += 1
        
        return outs
    
    def calculate_implied_odds(self, pot_size, bet_to_call, estimated_future_winnings):
        """
        Calculate implied odds considering future betting rounds
        """
        if bet_to_call <= 0:
            return float('inf')
            
        total_potential_winnings = pot_size + estimated_future_winnings
        return total_potential_winnings / bet_to_call
    
    def get_hand_strength_percentile(self, hero_cards, community_cards, num_opponents=1):
        # Normalization will happen inside calculate_equity_monte_carlo
        win_prob, _, _ = self.calculate_equity_monte_carlo(
            hero_cards, community_cards, num_opponents, simulations=500 # Using a fixed reasonable number of sims
        )
        return win_prob
