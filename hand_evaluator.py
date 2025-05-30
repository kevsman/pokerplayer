\
from itertools import combinations
import random # Add this import

class HandEvaluator:
    def __init__(self):
        self.rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14} # Added 'T': 10
        self.rank_map_rev = {v: k for k, v in self.rank_map.items()}
        # Sklansky-Malmuth hand groups (simplified)
        self.sklansky_groups = {
            1: ["AA", "KK", "QQ", "JJ", "AKs"],
            2: ["TT", "AQs", "AJs", "KQs", "AKo"],
            3: ["99", "ATs", "KJs", "QJs", "JTs", "AQo"],
            4: ["88", "KTs", "QTs", "J9s", "T9s", "98s", "AJo", "KQo"],
            5: ["77", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s", "K9s", "KJo", "QJo", "JTo"],
            6: ["66", "55", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s", "Q9s", "J8s", "T8s", "97s", "87s", "76s", "65s", "ATo", "KTo"],
            7: ["44", "33", "22", "Q8s", "T7s", "96s", "86s", "75s", "64s", "54s", "A9o", "K9o", "QTo", "J9o", "T9o", "98o"],
            8: ["A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o", "K8o", "K7o", "K6o", "K5o", "K4o", "K3o", "K2o", "Q9o", "J8o", "T8o", "97o", "87o", "76o", "65o", "54o"]
        }

    def deal_random_cards(self, deck_of_strings, num_cards):
        """
        Deals a specified number of random cards (strings) from the deck.
        Modifies the deck_of_strings in place by removing the dealt cards.
        Returns the list of dealt card strings.
        """
        if not isinstance(deck_of_strings, list):
            raise TypeError("Deck must be a list of card strings.")
        if len(deck_of_strings) < num_cards:
            raise ValueError(f"Not enough cards in deck ({len(deck_of_strings)}) to deal {num_cards} cards.")

        dealt_cards = random.sample(deck_of_strings, num_cards)
        
        for card in dealt_cards:
            deck_of_strings.remove(card) 
            
        return dealt_cards

    def _convert_card_to_value(self, card_str):
        if not card_str or len(card_str) < 2:
            return None
        
        rank_str = card_str[:-1]
        suit_char = card_str[-1]
        
        if rank_str not in self.rank_map:
            return None 
       
        # Allow both Unicode and simple char suits
        valid_suits_unicode = ['♠', '♥', '♦', '♣']
        valid_suits_char = ['s', 'h', 'd', 'c']
        
        standardized_suit = suit_char
        if suit_char in valid_suits_char:
            # Standardize to Unicode for internal representation, or choose one standard
            suit_map = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
            standardized_suit = suit_map[suit_char]
        elif suit_char not in valid_suits_unicode:
            return None
            
        return (self.rank_map[rank_str], standardized_suit)

    def _compare_tie_breakers(self, eval1_tie_breakers, eval2_tie_breakers):
        for r1, r2 in zip(eval1_tie_breakers, eval2_tie_breakers):
            if r1 > r2: return 1
            if r1 < r2: return -1
        return 0

    def _is_flush(self, hand_cards_processed, ranks, suits):
        first_suit = suits[0]
        is_flush = all(s == first_suit for s in suits)
        if is_flush:
            return True, first_suit, sorted(ranks, reverse=True)
        return False, None, []

    def _is_straight(self, ranks): # ranks: list of 5 distinct rank_values, sorted descending
        if ranks == [14, 5, 4, 3, 2]: # Ace-low straight (A,2,3,4,5)
            return True, 5, ranks 
        
        is_straight_seq = True
        for i in range(len(ranks) - 1):
            if ranks[i] != ranks[i+1] + 1:
                is_straight_seq = False
                break
        
        if is_straight_seq:
            return True, ranks[0], ranks
            
        return False, -1, []

    def _evaluate_five_card_hand(self, hand_cards_processed):
        hand_cards_processed.sort(key=lambda x: x[0], reverse=True)
        ranks = [card[0] for card in hand_cards_processed]
        suits = [card[1] for card in hand_cards_processed]

        is_flush_val, _, flush_ranks_val = self._is_flush(hand_cards_processed, ranks, suits)
        
        is_straight_val, straight_high_rank_val, straight_ranks_val = (False, -1, [])
        unique_ranks_for_straight = sorted(list(set(ranks)), reverse=True)
        if len(unique_ranks_for_straight) == 5:
             is_straight_val, straight_high_rank_val, straight_ranks_val = self._is_straight(unique_ranks_for_straight)

        # 1. Straight Flush
        if is_flush_val and is_straight_val:
            desc_high_card_rank = straight_high_rank_val
            desc = f"Straight Flush, {self.rank_map_rev.get(desc_high_card_rank, desc_high_card_rank)}-high"
            if sorted(straight_ranks_val, reverse=True) == [14, 13, 12, 11, 10]: # Royal Flush
                desc = "Royal Flush"
            return (9, desc, straight_ranks_val)

        rank_counts = {rank: ranks.count(rank) for rank in set(ranks)}

        # 2. Four of a Kind
        for rank_val, count in rank_counts.items():
            if count == 4:
                quad_rank_name = self.rank_map_rev.get(rank_val, rank_val)
                kicker = [r for r in ranks if r != rank_val][0]
                desc = f"Four of a Kind, {quad_rank_name}s"
                return (8, desc, [rank_val, kicker])
        
        # 3. Full House
        three_rank, pair_rank = -1, -1
        for r_val, count in rank_counts.items():
            if count == 3: three_rank = r_val
            if count == 2: pair_rank = r_val
        
        if three_rank != -1 and pair_rank != -1:
            three_name = self.rank_map_rev.get(three_rank, three_rank)
            pair_name = self.rank_map_rev.get(pair_rank, pair_rank)
            desc = f"Full House, {three_name}s full of {pair_name}s"
            return (7, desc, [three_rank, pair_rank])

        # 4. Flush
        if is_flush_val:
            high_card_name = self.rank_map_rev.get(flush_ranks_val[0], flush_ranks_val[0])
            desc = f"Flush, {high_card_name}-high"
            return (6, desc, flush_ranks_val)

        # 5. Straight
        if is_straight_val:
            high_card_name = self.rank_map_rev.get(straight_high_rank_val, straight_high_rank_val)
            desc = f"Straight, {high_card_name}-high"
            return (5, desc, straight_ranks_val)

        # 6. Three of a Kind
        if three_rank != -1: 
            three_name = self.rank_map_rev.get(three_rank, three_rank)
            kickers = sorted([r for r in ranks if r != three_rank], reverse=True)
            desc = f"Three of a Kind, {three_name}s"
            return (4, desc, [three_rank] + kickers[:2])

        # 7. Two Pair
        pairs_found = [r_val for r_val, count in rank_counts.items() if count == 2]
        if len(pairs_found) == 2:
            pairs_found.sort(reverse=True)
            p1_name = self.rank_map_rev.get(pairs_found[0], pairs_found[0])
            p2_name = self.rank_map_rev.get(pairs_found[1], pairs_found[1])
            kicker = [r for r in ranks if r not in pairs_found][0]
            desc = f"Two Pair, {p1_name}s and {p2_name}s"
            return (3, desc, [pairs_found[0], pairs_found[1], kicker])

        # 8. One Pair
        if len(pairs_found) == 1:
            pair_val = pairs_found[0]
            pair_name = self.rank_map_rev.get(pair_val, pair_val)
            kickers = sorted([r for r in ranks if r != pair_val], reverse=True)
            desc = f"One Pair, {pair_name}s"
            return (2, desc, [pair_val] + kickers[:3])
            
        # 9. High Card
        high_card_name = self.rank_map_rev.get(ranks[0], ranks[0])
        desc = f"High Card, {high_card_name}"
        return (1, desc, ranks)

    def calculate_best_hand(self, hole_cards, community_cards):
        all_cards_str = hole_cards + community_cards
        processed_cards = []
        for card_s in all_cards_str:
            conv_card = self._convert_card_to_value(card_s)
            if conv_card:
                processed_cards.append(conv_card)
        
        # Pre-flop: Return a basic evaluation (rank 0, description, sorted card ranks)
        if not community_cards: 
            if len(hole_cards) == 2:
                c1_str, c2_str = hole_cards[0], hole_cards[1]
                c1 = self._convert_card_to_value(c1_str)
                c2 = self._convert_card_to_value(c2_str)
                if c1 and c2:
                    r1_val, s1 = c1
                    r2_val, s2 = c2
                    
                    # Ensure r1_val is the higher rank for consistent tie-breaking/description
                    if r2_val > r1_val:
                        r1_val, r2_val = r2_val, r1_val
                        # s1 and s2 don't need to be swapped for rank list, but suit matters for description
                        original_s1, original_s2 = s1, s2 # Keep original suits for description
                        if hole_cards[0].startswith(self.rank_map_rev.get(r2_val)): # if c2_str was originally the higher card
                             s1, s2 = original_s2, original_s1
                        else:
                             s1, s2 = original_s1, original_s2


                    r1_name = self.rank_map_rev.get(r1_val, str(r1_val))
                    r2_name = self.rank_map_rev.get(r2_val, str(r2_val))
                    
                    desc = ""
                    if r1_val == r2_val:
                        desc = f"Pair of {r1_name}s"
                    else:
                        suited_str = " suited" if s1 == s2 else " offsuit"
                        desc = f"{r1_name}{r2_name}{suited_str}"
                    # For pre-flop, rank is 0 (less than any made hand), tie-breakers are card ranks
                    return (0, desc, sorted([r1_val, r2_val], reverse=True)) 
            return (0, "N/A (Pre-flop - invalid hole cards)", [])

        if len(processed_cards) < 5:
            # Return rank 0, description, and sorted processed card ranks if available
            current_ranks = sorted([card[0] for card in processed_cards], reverse=True)
            return (0, "N/A (Not enough cards for 5-card hand)", current_ranks)

        best_hand_rank_eval = (0, "High Card", []) # Default to lowest possible if no combo found

        for five_card_combo_processed in combinations(processed_cards, 5):
            current_hand_eval = self._evaluate_five_card_hand(list(five_card_combo_processed))
            
            if current_hand_eval[0] > best_hand_rank_eval[0]:
                best_hand_rank_eval = current_hand_eval
            elif current_hand_eval[0] == best_hand_rank_eval[0]:
                if self._compare_tie_breakers(current_hand_eval[2], best_hand_rank_eval[2]) > 0:
                    best_hand_rank_eval = current_hand_eval
        
        return best_hand_rank_eval # Return the full tuple

    def _get_hand_notation(self, card1_rank, card1_suit, card2_rank, card2_suit):
        r1 = self.rank_map_rev.get(card1_rank, str(card1_rank))
        r2 = self.rank_map_rev.get(card2_rank, str(card2_rank))
        
        # Order ranks: highest first
        if card1_rank < card2_rank:
            r1, r2 = r2, r1
            s1, s2 = card2_suit, card1_suit # Keep suits aligned with original cards for suitedness check
        else:
            s1, s2 = card1_suit, card2_suit

        if r1 == r2: # Pair
            return f"{r1}{r2}"
        else:
            suited_char = 's' if s1 == s2 else 'o'
            return f"{r1}{r2}{suited_char}"

    def evaluate_preflop_strength(self, hole_cards_str_list):
        if not hole_cards_str_list or len(hole_cards_str_list) != 2:
            return 0.0 # Invalid input

        card1_val = self._convert_card_to_value(hole_cards_str_list[0])
        card2_val = self._convert_card_to_value(hole_cards_str_list[1])

        if not card1_val or not card2_val:
            return 0.0 # Invalid card format

        hand_notation = self._get_hand_notation(card1_val[0], card1_val[1], card2_val[0], card2_val[1])
        
        for group_num, hands_in_group in self.sklansky_groups.items():
            if hand_notation in hands_in_group:
                # Higher group number means weaker hand, so invert for strength (e.g., 1 is strongest)
                # Max group is 8. Strength = (MaxGroup + 1 - GroupNum) / MaxGroup
                return (9 - group_num) / 8.0 
        
        return 0.1 # Default for very weak hands not in groups (should be rare with comprehensive groups)

    def evaluate_hand(self, hole_cards, community_cards):
        """Alias for calculate_best_hand to be used by DecisionEngine.
           Returns a dictionary including 'rank_category' and other details.
        """
        # calculate_best_hand returns a tuple: (rank_value, description, tie_breaker_ranks)
        # We need to adapt this to return a dictionary as expected by some parts of DecisionEngine
        # For now, let's assume DecisionEngine can handle the tuple or we adjust it there.
        # However, the error specifically mentions 'rank_category' from hand_strength_info.
        # So, we should return a dict.
        best_hand_tuple = self.calculate_best_hand(hole_cards, community_cards)
        if best_hand_tuple:
            # Example: ("Two Pair, Aces and Kings", [14, 13, 10])
            # The description string like "Two Pair, Aces and Kings" needs to be parsed or 
            # calculate_best_hand needs to return a more structured rank category.
            # For now, let's extract the primary rank category from the description.
            description = best_hand_tuple[1]
            rank_category = "N/A"
            if "Royal Flush" in description: rank_category = "Royal Flush"
            elif "Straight Flush" in description: rank_category = "Straight Flush"
            elif "Four of a Kind" in description: rank_category = "Four of a Kind"
            elif "Full House" in description: rank_category = "Full House"
            elif "Flush" in description: rank_category = "Flush"
            elif "Straight" in description: rank_category = "Straight"
            elif "Three of a Kind" in description: rank_category = "Three of a Kind"
            elif "Two Pair" in description: rank_category = "Two Pair"
            elif "One Pair" in description: rank_category = "One Pair"
            elif "High Card" in description: rank_category = "High Card"
            
            return {
                'rank_value': best_hand_tuple[0],
                'description': description,
                'tie_breakers': best_hand_tuple[2],
                'rank_category': rank_category, # This is what DecisionEngine expects
                'has_draw': False # Placeholder, add draw detection logic later
            }
        return {
            'rank_value': 0,
            'description': "N/A",
            'tie_breakers': [],
            'rank_category': "N/A",
            'has_draw': False
        }
