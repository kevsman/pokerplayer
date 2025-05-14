\
from itertools import combinations

class HandEvaluator:
    def __init__(self):
        self.rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        self.rank_map_rev = {v: k for k, v in self.rank_map.items()}

    def _convert_card_to_value(self, card_str):
        if not card_str or len(card_str) < 2:
            return None
        
        rank_str = card_str[:-1]
        suit_char = card_str[-1]
        
        if rank_str not in self.rank_map:
            return None 
        
        valid_suits = ['♠', '♥', '♦', '♣']
        if suit_char not in valid_suits:
            return None
            
        return (self.rank_map[rank_str], suit_char)

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
        
        if not community_cards: # Pre-flop
            if len(hole_cards) == 2:
                c1_str, c2_str = hole_cards[0], hole_cards[1]
                c1 = self._convert_card_to_value(c1_str)
                c2 = self._convert_card_to_value(c2_str)
                if c1 and c2:
                    r1_val, s1 = c1
                    r2_val, s2 = c2
                    
                    if r2_val > r1_val:
                        r1_val, r2_val = r2_val, r1_val
                        s1, s2 = s2, s1 
                    
                    r1_name = self.rank_map_rev.get(r1_val, str(r1_val))
                    r2_name = self.rank_map_rev.get(r2_val, str(r2_val))

                    if r1_val == r2_val:
                        return f"Pair of {r1_name}s"
                    else:
                        suited_str = " suited" if s1 == s2 else " offsuit"
                        return f"{r1_name}{r2_name}{suited_str}"
            return "N/A (Pre-flop)"

        if len(processed_cards) < 5:
            return "N/A (Not enough cards for 5-card hand)"

        best_hand_rank_eval = (0, "High Card", []) 

        for five_card_combo_processed in combinations(processed_cards, 5):
            current_hand_eval = self._evaluate_five_card_hand(list(five_card_combo_processed))
            
            if current_hand_eval[0] > best_hand_rank_eval[0]:
                best_hand_rank_eval = current_hand_eval
            elif current_hand_eval[0] == best_hand_rank_eval[0]:
                if self._compare_tie_breakers(current_hand_eval[2], best_hand_rank_eval[2]) > 0:
                    best_hand_rank_eval = current_hand_eval
        
        return best_hand_rank_eval[1]
