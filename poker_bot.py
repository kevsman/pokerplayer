from bs4 import BeautifulSoup
import re
import os
from itertools import combinations # New import

class PokerBot:
    def __init__(self, html_content):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.table_data = {}
        self.player_data = []

    def analyze_table(self):
        # Extract Hand ID
        hand_id_element = self.soup.find('div', class_='hand-id')
        if hand_id_element:
            self.table_data['hand_id'] = hand_id_element.text.strip().replace('#', '')
        else:
            self.table_data['hand_id'] = "N/A"

        # Extract pot size
        pot_element = self.soup.find('span', class_='total-pot-amount')
        if pot_element:
            pot_text = pot_element.text.strip()
            self.table_data['pot_size'] = pot_text
        else:
            self.table_data['pot_size'] = "N/A"

        # Extract community cards
        self.table_data['community_cards'] = []
        community_cards_container = self.soup.find('div', class_='community-cards')
        if community_cards_container:
            # Find card divs that are direct children of cardset-community and are not hidden
            cardset_community = community_cards_container.find('div', class_='cardset-community')
            if cardset_community:
                card_elements = cardset_community.find_all('div', class_='card', recursive=False)
                for card_element in card_elements:
                    if 'pt-visibility-hidden' in card_element.get('class', []):
                        continue # Skip hidden cards

                    card_str = "N/A"
                    # Try to get card from backup div first
                    card_backup = card_element.find('div', class_=re.compile(r'card-image-backup .*'))
                    if card_backup:
                        rank_element = card_backup.find('div', class_='card-rank')
                        suit_element = card_backup.find('div', class_='card-suit')
                        if rank_element and rank_element.text.strip() and suit_element and suit_element.text.strip():
                            card_str = rank_element.text.strip() + suit_element.text.strip()
                    
                    # Fallback to image src if backup didn't yield a card (or was incomplete)
                    if card_str == "N/A":
                        img_element = card_element.find('img', class_='card-image')
                        if img_element and img_element.get('src'):
                            src = img_element.get('src', '')
                            card_filename = src.split('/')[-1].split('.')[0] # e.g., "c5" or "dq"
                            if len(card_filename) >= 1: # Card rank can be 1 char (e.g. 'A') or 2 ('10')
                                suit_char = card_filename[0]
                                rank_char = card_filename[1:]
                                if not rank_char and len(card_filename) > 1: # Case like 's4' where rank is single digit
                                     rank_char = card_filename[0]
                                     suit_char = card_filename[1] if len(card_filename) >1 else card_filename[0] # handle single char like 'A' if it's a suit
                                     #This logic for single char needs review based on actual filenames
                                     # Assuming format like s4, cq, d10
                                     if card_filename[-1].isalpha(): # suit is last char
                                         suit_char = card_filename[-1]
                                         rank_char = card_filename[:-1]
                                     else: # suit is first char
                                         suit_char = card_filename[0]
                                         rank_char = card_filename[1:]

                                suit_map = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
                                card_str = rank_char.upper() + suit_map.get(suit_char.lower(), suit_char)
                                
                    if card_str != "N/A":
                         self.table_data['community_cards'].append(card_str)
        
        # Identify game stage based on number of community cards
        num_cards = len(self.table_data['community_cards'])
        if num_cards == 0:
            self.table_data['game_stage'] = 'Preflop'
        elif num_cards == 3:
            self.table_data['game_stage'] = 'Flop'
        elif num_cards == 4:
            self.table_data['game_stage'] = 'Turn'
        elif num_cards == 5:
            self.table_data['game_stage'] = 'River'
        else:
            self.table_data['game_stage'] = 'Unknown'
            
        # Identify dealer position
        self.table_data['dealer_position'] = "N/A"
        # Find the dealer button that is NOT hidden and its ID does not end with '-hidden'
        dealer_buttons = self.soup.find_all('div', class_='dealer', id=re.compile(r'dealer-seat-\d+$'))
        for btn in dealer_buttons:
            # Check if the button itself or its direct game-position parent is hidden
            parent_game_pos = btn.find_parent('div', class_=re.compile(r'game-position-'))
            is_hidden = 'pt-visibility-hidden' in btn.get('class', [])
            if parent_game_pos and 'pt-visibility-hidden' in parent_game_pos.get('class', []):
                is_hidden = True
            
            if not is_hidden:
                dealer_id = btn.get('id', '') # e.g., "dealer-seat-1"
                if 'dealer-seat-' in dealer_id:
                    self.table_data['dealer_position'] = dealer_id.split('-')[-1]
                    break 

    def analyze_players(self):
        self.player_data = [] # Reset player data
        
        # Corrected player_elements selection
        potential_player_elements = self.soup.find_all('div', class_='player-area')
        player_elements = []
        for el in potential_player_elements:
            if any(re.match(r'player-seat-\\d+', c) for c in el.get('class', [])):
                player_elements.append(el)
        
        for player_element in player_elements:
            player_info = {
                'seat': None, 'name': 'N/A', 'stack': 'N/A', 'bet': '0', 
                'is_my_player': False, 'is_empty': False, 'cards': [], 
                'has_turn': False, 'has_hidden_cards': False,
                'hand_rank': 'N/A'
            }

            seat_class = next((cls for cls in player_element.get('class', []) if cls.startswith('player-seat-')), None)
            if seat_class:
                player_info['seat'] = seat_class.split('-')[-1]

            if 'my-player' in player_element.get('class', []):
                player_info['is_my_player'] = True
            
            empty_seat_element = player_element.find('div', class_='empty-seat')
            if empty_seat_element and empty_seat_element.text.strip().lower() == 'empty':
                player_info['is_empty'] = True
                self.player_data.append(player_info)
                continue

            name_element = player_element.find('div', class_='text-block nickname')
            if name_element:
                target_name_element = name_element.find('div', class_='target')
                if target_name_element:
                    player_info['name'] = target_name_element.text.strip()
                else: 
                    editable_span = name_element.find('span', class_='editable')
                    if editable_span:
                         player_info['name'] = editable_span.text.strip()
                    elif name_element.text.strip() and name_element.text.strip().lower() != 'empty': # Fallback
                         player_info['name'] = name_element.text.strip()

            # If it's my player and name is still N/A, try global username
            if player_info['is_my_player'] and player_info['name'] == 'N/A':
                global_user_info = self.soup.find('div', class_='user-info')
                if global_user_info:
                    editable_name_span = global_user_info.find('span', class_='editable')
                    if editable_name_span and editable_name_span.text.strip():
                        player_info['name'] = editable_name_span.text.strip()
            
            stack_element = player_element.find('div', class_='text-block amount')
            if stack_element:
                player_info['stack'] = stack_element.text.strip()
            
            bet_container = player_element.find('div', class_='player-bet')
            if bet_container:
                bet_amount_element = bet_container.find('div', class_='amount')
                if bet_amount_element and bet_amount_element.text.strip():
                    player_info['bet'] = bet_amount_element.text.strip()
            
            # Revised has_turn detection
            player_info['has_turn'] = False
            table_player_div = player_element.find('div', class_='table-player')
            if table_player_div and 'player-active' in table_player_div.get('class', []):
                player_info['has_turn'] = True
            
            if not player_info['has_turn']: # Check other indicators if not already set
                nameplate_div = player_element.find('div', class_='player-nameplate')
                if nameplate_div:
                    countdown_div = nameplate_div.find('div', class_='text-countdown')
                    if countdown_div and 'pt-hidden' not in countdown_div.get('class', []):
                        # Basic check, ideally traverse parents for pt-hidden too
                        is_parent_hidden = False
                        parent = countdown_div.parent
                        while parent and parent != nameplate_div and parent.name != 'body':
                            if 'pt-hidden' in parent.get('class', []) or \
                               'pt-visibility-hidden' in parent.get('class', []):
                                is_parent_hidden = True
                                break
                            parent = parent.parent
                        if not is_parent_hidden:
                            player_info['has_turn'] = True
                    
                    if not player_info['has_turn']: # Check timeout-wrapper if still not found
                        timeout_wrapper_div = nameplate_div.find('div', class_='timeout-wrapper')
                        if timeout_wrapper_div and 'pt-hidden' not in timeout_wrapper_div.get('class', []):
                            is_parent_hidden = False # Reset for this check
                            parent = timeout_wrapper_div.parent
                            while parent and parent != nameplate_div and parent.name != 'body':
                                if 'pt-hidden' in parent.get('class', []) or \
                                   'pt-visibility-hidden' in parent.get('class', []):
                                    is_parent_hidden = True
                                    break
                                parent = parent.parent
                            if not is_parent_hidden:
                                player_info['has_turn'] = True
            
            if player_info['is_my_player']:
                cards_holder = player_element.find('div', class_='cards-holder-hero')
                if cards_holder:
                    card_divs = cards_holder.find_all('div', class_=re.compile(r'card\d*')) 
                    for card_div in card_divs:
                        if 'pt-visibility-hidden' in card_div.get('class', []): continue

                        card_str = "N/A"
                        card_backup = card_div.find('div', class_=re.compile(r'card-image-backup .*'))
                        if card_backup:
                            rank_el = card_backup.find('div', class_='card-rank')
                            suit_el = card_backup.find('div', class_='card-suit')
                            if rank_el and rank_el.text.strip() and suit_el and suit_el.text.strip():
                                card_str = rank_el.text.strip() + suit_el.text.strip()
                        
                        if card_str == "N/A": # Fallback to image if backup failed
                            img_element = card_div.find('img', class_='card-image')
                            if img_element and img_element.get('src'):
                                src = img_element.get('src', '')
                                card_filename = src.split('/')[-1].split('.')[0]
                                if len(card_filename) >= 1:
                                    # Assuming format like s4, cq, d10 (suit char + rank char(s))
                                    # Or rank char(s) + suit char for some conventions
                                    # For dq.svg -> D♦, s4.svg -> 4♠
                                    suit_char = ''
                                    rank_char = ''
                                    if card_filename[-1].isalpha() and not card_filename[-1].isdigit(): # dQ, s4
                                        suit_char = card_filename[-1]
                                        rank_char = card_filename[:-1]
                                    elif card_filename[0].isalpha() and not card_filename[0].isdigit(): # Qd, 4s
                                        suit_char = card_filename[0]
                                        rank_char = card_filename[1:]
                                    
                                    if suit_char and rank_char:
                                        suit_map = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
                                        card_str = rank_char.upper() + suit_map.get(suit_char.lower(), suit_char)
                        
                        if card_str != "N/A":
                            player_info['cards'].append(card_str)
                
                # Calculate hand rank if cards are parsed and table data is available
                if player_info['cards'] and self.table_data: # Ensure table_data is populated
                    community_cards = self.table_data.get('community_cards', [])
                    player_info['hand_rank'] = self._calculate_best_hand(player_info['cards'], community_cards)
            else: # Other players - check for hidden cards
                cards_holder_other = player_element.find('div', class_='cards-holder-other-hidden')
                if cards_holder_other:
                    card_images = cards_holder_other.find_all('img', class_='card-image')
                    if card_images: # Presence of card images (even backs) means they have cards
                        player_info['has_hidden_cards'] = True
            
            self.player_data.append(player_info)

    def get_active_player(self):
        for player in self.player_data:
            if player.get('has_turn', False):
                return player
        return None
        
    def get_my_player(self):
        for player in self.player_data:
            if player.get('is_my_player', False):
                return player
        return None

    def analyze(self):
        self.analyze_table() # Ensure table data is analyzed first
        self.analyze_players()
        return {
            'table': self.table_data,
            'players': self.player_data,
            'my_player': self.get_my_player(),
            'active_player': self.get_active_player()
        }
    
    def get_summary(self):
        if not self.table_data and not self.player_data: 
            self.analyze() # This calls analyze_table then analyze_players
            
        summary = []
        summary.append(f"--- Table --- Hand ID: {self.table_data.get('hand_id', 'N/A')}")
        summary.append(f"Pot: {self.table_data.get('pot_size', 'N/A')}")
        summary.append(f"Game Stage: {self.table_data.get('game_stage', 'N/A')}")
        
        cc_list = self.table_data.get('community_cards', [])
        cc_text = ' '.join(cc_list) if cc_list else "None"
        summary.append(f"Community Cards: {cc_text}")
        summary.append(f"Dealer Position: Seat {self.table_data.get('dealer_position', 'N/A')}")
        
        summary.append("\n--- Players ---")
        if not self.player_data:
            summary.append("  No player data found or analyzed.")
        
        sorted_players = sorted(self.player_data, key=lambda p: int(p['seat']) if p['seat'] and p['seat'].isdigit() else 999)

        for player in sorted_players:
            if player.get('is_empty', False):
                summary.append(f"  Seat {player.get('seat', 'N/A')}: Empty")
                continue
                
            name = player.get('name', 'N/A')
            stack = player.get('stack', 'N/A')
            bet = player.get('bet', '0') 
            
            status = []
            if player.get('is_my_player', False):
                status.append("ME")
                hand_rank_str = player.get('hand_rank')
                if hand_rank_str and hand_rank_str != 'N/A':
                    status.append(f"Hand: {hand_rank_str}")

            if player.get('has_turn', False): status.append("ACTIVE TURN")
            status_text = f" ({', '.join(status)})" if status else ""
            
            cards_text = ""
            if player.get('cards') and player['cards']:
                cards_text = f" Cards: {' '.join(player.get('cards'))}"
            elif player.get('has_hidden_cards', False):
                cards_text = " (Has hidden cards)"
                
            summary.append(f"  Seat {player.get('seat', 'N/A')}: {name}{status_text} - Stack: {stack}, Bet: {bet}{cards_text}")
        
        active_player = self.get_active_player()
        if active_player:
            summary.append(f"\nIt is currently Seat {active_player['seat']} ({active_player['name']})'s turn.")
        else:
            summary.append("\nNo player currently has the turn (or turn detection failed).")
            
        my_player = self.get_my_player()
        if my_player and my_player.get('has_turn'):
            summary.append("It is YOUR turn to act.")

        return "\n".join(summary)

    # --- Hand Ranking Logic ---
    def _get_rank_map(self):
        return {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

    def _convert_card_to_value(self, card_str):
        if not card_str or len(card_str) < 2:
            return None
        
        rank_str = card_str[:-1]
        suit_char = card_str[-1]

        rank_map = self._get_rank_map()
        
        if rank_str not in rank_map:
            # Handle '10' rank case if it's parsed as '1' '0' separately by upstream.
            # Assuming card_str is "10♠", rank_str is "10".
            return None 
        
        valid_suits = ['♠', '♥', '♦', '♣']
        if suit_char not in valid_suits:
            return None
            
        return (rank_map[rank_str], suit_char)

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
        
        rank_map_rev = {v: k for k, v in self._get_rank_map().items()}

        is_flush_val, _, flush_ranks_val = self._is_flush(hand_cards_processed, ranks, suits)
        
        is_straight_val, straight_high_rank_val, straight_ranks_val = (False, -1, [])
        unique_ranks_for_straight = sorted(list(set(ranks)), reverse=True)
        if len(unique_ranks_for_straight) == 5:
             is_straight_val, straight_high_rank_val, straight_ranks_val = self._is_straight(unique_ranks_for_straight)

        # 1. Straight Flush
        if is_flush_val and is_straight_val:
            # The straight_ranks_val are from unique_ranks_for_straight, which are the ranks of the 5 cards.
            # If it's a flush and these 5 unique ranks form a straight, it's a straight flush.
            desc_high_card_rank = straight_high_rank_val
            desc = f"Straight Flush, {rank_map_rev.get(desc_high_card_rank, desc_high_card_rank)}-high"
            if sorted(straight_ranks_val, reverse=True) == [14, 13, 12, 11, 10]: # Royal Flush
                desc = "Royal Flush"
            # Ace-low straight flush (5-high) is covered by straight_high_rank_val being 5.
            return (9, desc, straight_ranks_val)

        rank_counts = {rank: ranks.count(rank) for rank in set(ranks)}

        # 2. Four of a Kind
        for rank_val, count in rank_counts.items():
            if count == 4:
                quad_rank_name = rank_map_rev.get(rank_val, rank_val)
                kicker = [r for r in ranks if r != rank_val][0]
                desc = f"Four of a Kind, {quad_rank_name}s"
                return (8, desc, [rank_val, kicker])
        
        # 3. Full House
        three_rank, pair_rank = -1, -1
        for r_val, count in rank_counts.items():
            if count == 3: three_rank = r_val
            if count == 2: pair_rank = r_val
        
        if three_rank != -1 and pair_rank != -1:
            three_name = rank_map_rev.get(three_rank, three_rank)
            pair_name = rank_map_rev.get(pair_rank, pair_rank)
            desc = f"Full House, {three_name}s full of {pair_name}s"
            return (7, desc, [three_rank, pair_rank])

        # 4. Flush
        if is_flush_val:
            high_card_name = rank_map_rev.get(flush_ranks_val[0], flush_ranks_val[0])
            desc = f"Flush, {high_card_name}-high"
            return (6, desc, flush_ranks_val)

        # 5. Straight
        if is_straight_val:
            high_card_name = rank_map_rev.get(straight_high_rank_val, straight_high_rank_val)
            desc = f"Straight, {high_card_name}-high"
            return (5, desc, straight_ranks_val)

        # 6. Three of a Kind
        if three_rank != -1: # (and no pair for Full House)
            three_name = rank_map_rev.get(three_rank, three_rank)
            kickers = sorted([r for r in ranks if r != three_rank], reverse=True)
            desc = f"Three of a Kind, {three_name}s"
            return (4, desc, [three_rank] + kickers[:2])

        # 7. Two Pair
        pairs_found = [r_val for r_val, count in rank_counts.items() if count == 2]
        if len(pairs_found) == 2:
            pairs_found.sort(reverse=True)
            p1_name = rank_map_rev.get(pairs_found[0], pairs_found[0])
            p2_name = rank_map_rev.get(pairs_found[1], pairs_found[1])
            kicker = [r for r in ranks if r not in pairs_found][0]
            desc = f"Two Pair, {p1_name}s and {p2_name}s"
            return (3, desc, [pairs_found[0], pairs_found[1], kicker])

        # 8. One Pair
        if len(pairs_found) == 1:
            pair_val = pairs_found[0]
            pair_name = rank_map_rev.get(pair_val, pair_val)
            kickers = sorted([r for r in ranks if r != pair_val], reverse=True)
            desc = f"One Pair, {pair_name}s"
            return (2, desc, [pair_val] + kickers[:3])
            
        # 9. High Card
        high_card_name = rank_map_rev.get(ranks[0], ranks[0])
        desc = f"High Card, {high_card_name}"
        return (1, desc, ranks)

    def _calculate_best_hand(self, hole_cards, community_cards):
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
                    rank_map = self._get_rank_map()
                    rank_names_rev = {v: k for k, v in rank_map.items()}
                    r1_val, s1 = c1
                    r2_val, s2 = c2
                    
                    # Order by rank for consistent naming (e.g., AK not KA)
                    if r2_val > r1_val:
                        r1_val, r2_val = r2_val, r1_val
                        s1, s2 = s2, s1 # Keep suits aligned for suitedness check
                    
                    r1_name = rank_names_rev.get(r1_val, str(r1_val))
                    r2_name = rank_names_rev.get(r2_val, str(r2_val))

                    if r1_val == r2_val:
                        return f"Pair of {r1_name}s"
                    else:
                        suited_str = " suited" if s1 == s2 else " offsuit"
                        return f"{r1_name}{r2_name}{suited_str}"
            return "N/A (Pre-flop)"

        if len(processed_cards) < 5:
            return "N/A (Not enough cards for 5-card hand)"

        best_hand_rank_eval = (0, "High Card", []) # (strength, description, tie_breakers)

        for five_card_combo_processed in combinations(processed_cards, 5):
            current_hand_eval = self._evaluate_five_card_hand(list(five_card_combo_processed))
            
            if current_hand_eval[0] > best_hand_rank_eval[0]:
                best_hand_rank_eval = current_hand_eval
            elif current_hand_eval[0] == best_hand_rank_eval[0]:
                if self._compare_tie_breakers(current_hand_eval[2], best_hand_rank_eval[2]) > 0:
                    best_hand_rank_eval = current_hand_eval
        
        return best_hand_rank_eval[1]

if __name__ == "__main__":
    import sys
    import os # Ensure os is imported if not already at the top level of __main__

    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_html_file_path = os.path.join(script_dir, "examples", "preflop_not_my_turn.html")
    
    html_file_path = default_html_file_path
    if len(sys.argv) > 1:
        html_file_path = sys.argv[1]
        if not os.path.isabs(html_file_path):
             html_file_path = os.path.join(script_dir, html_file_path) # Allow relative paths from script dir
    
    if not os.path.exists(html_file_path):
        print(f"Error: HTML file not found at {html_file_path}")
        # Try to list files in examples directory if default was used and not found
        if html_file_path == default_html_file_path:
            example_dir = os.path.join(script_dir, "examples")
            if os.path.exists(example_dir):
                print(f"Available files in {example_dir}:")
                for f_name in os.listdir(example_dir):
                    print(f"  - {f_name}")
            else:
                print(f"Example directory not found: {example_dir}")
        sys.exit(1)

    try:
        print(f"Attempting to open and parse: {html_file_path}")
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content_example = file.read()
        
        bot = PokerBot(html_content_example)
        
        print("\n---- Summary from PokerBot ----")
        print(bot.get_summary())

        print("\n---- Raw Analysis Result (for debugging) ----")
        import json
        # Ensure analysis is done if get_summary didn't run it or if we want the direct result
        analysis_result = bot.analyze() 
        print(json.dumps(analysis_result, indent=2))


    except FileNotFoundError:
        # This specific exception might be redundant due to the check above, but good for safety
        print(f"Error: HTML file could not be opened (FileNotFound): {html_file_path}")
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        import traceback
        traceback.print_exc()

