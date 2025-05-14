from bs4 import BeautifulSoup
import re
import os

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
        player_elements = self.soup.find_all('div', class_=re.compile(r'player-area player-seat-\d+'))
        
        for player_element in player_elements:
            player_info = {
                'seat': None, 'name': 'N/A', 'stack': 'N/A', 'bet': '0', 
                'is_my_player': False, 'is_empty': False, 'cards': [], 
                'has_turn': False, 'has_hidden_cards': False
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
                continue # Skip other details for empty seats

            name_element = player_element.find('div', class_='text-block nickname')
            if name_element:
                target_name_element = name_element.find('div', class_='target')
                if target_name_element:
                    player_info['name'] = target_name_element.text.strip()
                else: 
                    editable_span = name_element.find('span', class_='editable') # For current player's name
                    if editable_span:
                         player_info['name'] = editable_span.text.strip()
                    elif name_element.text.strip(): # Fallback if no target/editable but text exists
                         player_info['name'] = name_element.text.strip()

            stack_element = player_element.find('div', class_='text-block amount')
            if stack_element:
                player_info['stack'] = stack_element.text.strip()
            
            bet_container = player_element.find('div', class_='player-bet')
            if bet_container:
                bet_amount_element = bet_container.find('div', class_='amount')
                if bet_amount_element and bet_amount_element.text.strip():
                    player_info['bet'] = bet_amount_element.text.strip()
            
            # Check for player's turn (active player timer)
            player_timer_div = player_element.find('div', class_='player-timer')
            if player_timer_div and 'pt-hidden' not in player_timer_div.get('class', []):
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
        self.analyze_table()
        self.analyze_players()
        return {
            'table': self.table_data,
            'players': self.player_data,
            'my_player': self.get_my_player(),
            'active_player': self.get_active_player()
        }
    
    def get_summary(self):
        if not self.table_data and not self.player_data: 
            self.analyze()
            
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
            if player.get('is_my_player', False): status.append("ME")
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

if __name__ == "__main__":
    import sys

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

        # print("\n---- Raw Analysis Result (for debugging) ----")
        # import json
        # analysis_result = bot.analyze() # Ensure analysis is done if not by get_summary
        # print(json.dumps(analysis_result, indent=2))


    except FileNotFoundError:
        # This specific exception might be redundant due to the check above, but good for safety
        print(f"Error: HTML file could not be opened (FileNotFound): {html_file_path}")
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        import traceback
        traceback.print_exc()

