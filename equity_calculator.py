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
        total_simulations_count = 0

        raw_player_cards_input = hole_cards_str_list[0]
        player_hole_cards_str_list_for_conversion = []
        if isinstance(raw_player_cards_input, str):
            player_hole_cards_str_list_for_conversion = [raw_player_cards_input]
        elif isinstance(raw_player_cards_input, list):
            player_hole_cards_str_list_for_conversion = raw_player_cards_input
        else:
            logger.error(f"Unexpected type for player hole cards input: {type(raw_player_cards_input)}. Value: {raw_player_cards_input}")
            return 0.0, 0.0, 0.0
        
        # Ensure community_cards_str_list is a list, even if empty
        community_cards_str_list = community_cards_str_list if community_cards_str_list is not None else []

        # 1. Prepare known cards as strings
        known_cards_strings = player_hole_cards_str_list_for_conversion + community_cards_str_list

        # 2. Generate initial string deck and filter known cards (strings) from it
        deck_strings = self._generate_deck()
        deck_strings = [c for c in deck_strings if c not in known_cards_strings]

        # 3. Convert player and community cards to HandEvaluator's internal object format for evaluation
        player_hole_cards_obj = []
        community_cards_obj = []
        try:
            player_hole_cards_obj = [self.hand_evaluator._convert_card_to_value(c) for c in player_hole_cards_str_list_for_conversion]
            player_hole_cards_obj = [c for c in player_hole_cards_obj if c is not None]

            if community_cards_str_list:
                community_cards_obj = [self.hand_evaluator._convert_card_to_value(c) for c in community_cards_str_list]
                community_cards_obj = [c for c in community_cards_obj if c is not None]

            if len(player_hole_cards_obj) != len(player_hole_cards_str_list_for_conversion):
                logger.error(f"Failed to convert all player hole cards. Input: {player_hole_cards_str_list_for_conversion} -> Converted: {player_hole_cards_obj}")
                return 0.0, 0.0, 0.0
            if community_cards_str_list and len(community_cards_obj) != len(community_cards_str_list):
                logger.warning(f"Failed to convert some community cards. Input: {community_cards_str_list} -> Converted: {community_cards_obj}")
        except Exception as e:
            logger.error(f"Error during initial card conversion to objects: {e}", exc_info=True)
            return 0.0, 0.0, 0.0

        for i in range(num_simulations):
            current_deck_sim_strings = list(deck_strings) # Use the correctly pre-filtered string deck
            
            try:
                num_board_cards_needed = 5 - len(community_cards_obj)
                
                # Check if enough cards for opponent + board
                required_cards_for_sim = 2 + max(0, num_board_cards_needed)
                if len(current_deck_sim_strings) < required_cards_for_sim:
                    logger.debug(f"Sim {i}: Not enough cards in deck ({len(current_deck_sim_strings)}) for simulation. Need {required_cards_for_sim}. Skipping.")
                    continue                # Deal opponent hand (strings) - use random.sample without modifying deck
                import random
                if len(current_deck_sim_strings) < 2:
                    logger.debug(f"Sim {i}: Not enough cards for opponent hand. Deck: {len(current_deck_sim_strings)}. Skipping.")
                    continue
                opponent_hole_cards_strings = random.sample(current_deck_sim_strings, 2)
                
                # Remove opponent cards from available deck for board dealing
                remaining_deck = [c for c in current_deck_sim_strings if c not in opponent_hole_cards_strings]
                
                # Deal remaining board cards (strings)
                additional_board_cards_strings = []
                if num_board_cards_needed > 0:
                    if len(remaining_deck) < num_board_cards_needed:
                        logger.debug(f"Sim {i}: Not enough cards for additional board. Deck: {len(remaining_deck)}, Need: {num_board_cards_needed}. Skipping.")
                        continue
                    additional_board_cards_strings = random.sample(remaining_deck, num_board_cards_needed)
                
                # Convert dealt string cards to HandEvaluator's object format for evaluation
                opponent_hole_cards_sim_obj = [self.hand_evaluator._convert_card_to_value(c) for c in opponent_hole_cards_strings]
                opponent_hole_cards_sim_obj = [c for c in opponent_hole_cards_sim_obj if c is not None]

                additional_board_cards_obj = [self.hand_evaluator._convert_card_to_value(c) for c in additional_board_cards_strings]
                additional_board_cards_obj = [c for c in additional_board_cards_obj if c is not None]

                if len(opponent_hole_cards_sim_obj) != 2:
                    logger.debug(f"Sim {i}: Opponent card conversion resulted in != 2 cards. Strings: {opponent_hole_cards_strings}, Objs: {opponent_hole_cards_sim_obj}. Skipping.")
                    continue
                
                if num_board_cards_needed > 0 and len(additional_board_cards_obj) != num_board_cards_needed:
                    logger.debug(f"Sim {i}: Additional board card conversion resulted in wrong count. Strings: {additional_board_cards_strings}, Objs: {additional_board_cards_obj}, Needed: {num_board_cards_needed}. Skipping.")
                    continue

                current_board_sim_obj = community_cards_obj + additional_board_cards_obj

                if len(current_board_sim_obj) > 5:
                     logger.warning(f"Sim {i}: Board length > 5 ({len(current_board_sim_obj)}). Board: {self.hand_evaluator.cards_to_strings(current_board_sim_obj) if hasattr(self.hand_evaluator, 'cards_to_strings') else current_board_sim_obj}. Skipping.")
                     continue

                # Use string cards for evaluation (evaluate_hand expects strings, not tuples)
                current_board_sim_strings = community_cards_str_list + additional_board_cards_strings
                player_eval = self.hand_evaluator.evaluate_hand(player_hole_cards_str_list_for_conversion, current_board_sim_strings)
                opponent_eval = self.hand_evaluator.evaluate_hand(opponent_hole_cards_strings, current_board_sim_strings)
                comparison_result_for_log = self._compare_hands(player_eval, opponent_eval)

                if i < 5: # Log details for the first 5 simulations for debugging
                    sim_board_strings_log = community_cards_str_list + additional_board_cards_strings
                    
                    # Assuming player_hole_cards_str_list_for_conversion and opponent_hole_cards_strings are lists of strings
                    player_hole_cards_str_log = player_hole_cards_str_list_for_conversion
                    opponent_hole_cards_str_log = opponent_hole_cards_strings

                    logger.debug(f"SIM_DEBUG #{i}: PlayerHole: {player_hole_cards_str_log}, OpponentHole: {opponent_hole_cards_str_log}, Board: {sim_board_strings_log}")
                    logger.debug(f"SIM_DEBUG #{i}: PlayerEval Rank: {player_eval.get('rank_value')}, Desc: {player_eval.get('description')}, Tiebreakers: {player_eval.get('tie_breakers')}")
                    logger.debug(f"SIM_DEBUG #{i}: OpponentEval Rank: {opponent_eval.get('rank_value')}, Desc: {opponent_eval.get('description')}, Tiebreakers: {opponent_eval.get('tie_breakers')}")
                    logger.debug(f"SIM_DEBUG #{i}: ComparisonResult: {comparison_result_for_log}")

                if comparison_result_for_log > 0:
                    player_wins += 1
                elif comparison_result_for_log == 0:
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
        equity = win_probability + (tie_probability / 2) # Corrected equity calculation

        logger.info(
            f"Equity calculation complete for {player_hole_cards_str_list_for_conversion} vs random. "
            f"Win: {win_probability*100:.2f}%, Tie: {tie_probability*100:.2f}%, Equity: {equity*100:.2f}% "
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
            hero_cards, community_cards, num_opponents, simulations=500  # Using a fixed reasonable number of sims
        )
        return win_prob
    
    def calculate_win_probability(self, hole_cards, community_cards, num_opponents=1):
        """
        Calculate win probability against random opponents.
        This is a wrapper method around calculate_equity_monte_carlo for compatibility.
        
        Args:
            hole_cards: Hero's hole cards (tuple or list format)
            community_cards: Community cards (list)
            num_opponents: Number of opponents (default 1)
            
        Returns:
            float: Win probability (0.0 to 1.0)
        """
        def convert_tuple_cards_to_strings(cards):
            """Convert tuple format cards to string format"""
            if not cards:
                return []
            
            converted_cards = []
            for card in cards:
                if isinstance(card, tuple) and len(card) == 2:
                    rank, suit = card
                    # Convert suit names to symbols
                    suit_map = {
                        'SPADES': '♠', 'HEARTS': '♥', 'DIAMONDS': '♦', 'CLUBS': '♣',
                        'SPADE': '♠', 'HEART': '♥', 'DIAMOND': '♦', 'CLUB': '♣'
                    }
                    suit_symbol = suit_map.get(suit.upper(), suit)
                    # Handle 10 vs T representation
                    rank_str = '10' if rank == 'T' else rank
                    converted_cards.append(rank_str + suit_symbol)
                elif isinstance(card, str):
                    # Already in string format
                    converted_cards.append(card)
                else:
                    logger.warning(f"Unexpected card format: {card}")
            return converted_cards
        
        # Convert hole cards from tuple format if needed
        if isinstance(hole_cards, (list, tuple)):
            hole_cards = convert_tuple_cards_to_strings(hole_cards)
        else:
            logger.error(f"Unexpected hole_cards format: {type(hole_cards)} - {hole_cards}")
            return 0.0
        
        # Convert community cards from tuple format if needed
        if isinstance(community_cards, (list, tuple)):
            community_cards = convert_tuple_cards_to_strings(community_cards)
        else:
            community_cards = []
        
        # Validate that we have exactly 2 hole cards
        if len(hole_cards) != 2:
            logger.error(f"Invalid number of hole cards: {len(hole_cards)} - {hole_cards}")
            return 0.0
        
        # The monte carlo method expects [hole_cards_list], community_cards, opponent_range, num_simulations
        win_prob, _, _ = self.calculate_equity_monte_carlo(
            [hole_cards], community_cards, None, 500  # 500 simulations for reasonable speed
        )
        return win_prob
