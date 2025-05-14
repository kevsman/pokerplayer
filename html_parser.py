from bs4 import BeautifulSoup
import re

class PokerPageParser:
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
            cardset_community = community_cards_container.find('div', class_='cardset-community')
            if cardset_community:
                card_elements = cardset_community.find_all('div', class_='card', recursive=False)
                for card_element in card_elements:
                    if 'pt-visibility-hidden' in card_element.get('class', []):
                        continue

                    card_str = "N/A"
                    card_backup = card_element.find('div', class_=re.compile(r'card-image-backup .*'))
                    if card_backup:
                        rank_element = card_backup.find('div', class_='card-rank')
                        suit_element = card_backup.find('div', class_='card-suit')
                        if rank_element and rank_element.text.strip() and suit_element and suit_element.text.strip():
                            card_str = rank_element.text.strip() + suit_element.text.strip()
                    
                    if card_str == "N/A":
                        img_element = card_element.find('img', class_='card-image')
                        if img_element and img_element.get('src'):
                            src = img_element.get('src', '')
                            card_filename = src.split('/')[-1].split('.')[0]
                            if len(card_filename) >= 1:
                                suit_char = card_filename[0]
                                rank_char = card_filename[1:]
                                # Basic extraction, might need refinement based on actual filename patterns
                                suit_map = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
                                card_str = rank_char.upper() + suit_map.get(suit_char.lower(), suit_char)
                                
                    if card_str != "N/A":
                         self.table_data['community_cards'].append(card_str)
        
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
            
        self.table_data['dealer_position'] = "N/A"
        dealer_buttons = self.soup.find_all('div', class_='dealer', id=re.compile(r'dealer-seat-\d+$'))
        for btn in dealer_buttons:
            parent_game_pos = btn.find_parent('div', class_=re.compile(r'game-position-'))
            is_hidden = 'pt-visibility-hidden' in btn.get('class', [])
            if parent_game_pos and 'pt-visibility-hidden' in parent_game_pos.get('class', []):
                is_hidden = True
            
            if not is_hidden:
                dealer_id = btn.get('id', '')
                if 'dealer-seat-' in dealer_id:
                    self.table_data['dealer_position'] = dealer_id.split('-')[-1]
                    break 
        return self.table_data

    def analyze_players(self):
        self.player_data = [] 
        
        potential_player_elements = self.soup.find_all('div', class_='player-area')
        player_elements = []
        for el in potential_player_elements:
            if any(re.match(r'player-seat-\d+', c) for c in el.get('class', [])):
                player_elements.append(el)
        
        for player_element in player_elements:
            player_info = {
                'seat': None, 'name': 'N/A', 'stack': 'N/A', 'bet': '0', 
                'is_my_player': False, 'is_empty': False, 'cards': [], 
                'has_turn': False, 'has_hidden_cards': False
                # 'hand_rank' will be calculated by PokerBot using HandEvaluator
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
                    elif name_element.text.strip() and name_element.text.strip().lower() != 'empty':
                         player_info['name'] = name_element.text.strip()

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
            
            player_info['has_turn'] = False
            table_player_div = player_element.find('div', class_='table-player')
            if table_player_div and 'player-active' in table_player_div.get('class', []):
                player_info['has_turn'] = True
            
            if not player_info['has_turn']:
                nameplate_div = player_element.find('div', class_='player-nameplate')
                if nameplate_div:
                    countdown_div = nameplate_div.find('div', class_='text-countdown')
                    if countdown_div and 'pt-hidden' not in countdown_div.get('class', []):
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
                    
                    if not player_info['has_turn']: 
                        timeout_wrapper_div = nameplate_div.find('div', class_='timeout-wrapper')
                        if timeout_wrapper_div and 'pt-hidden' not in timeout_wrapper_div.get('class', []):
                            is_parent_hidden = False
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
                        
                        if card_str == "N/A": 
                            img_element = card_div.find('img', class_='card-image')
                            if img_element and img_element.get('src'):
                                src = img_element.get('src', '')
                                card_filename = src.split('/')[-1].split('.')[0]
                                if len(card_filename) >= 1:
                                    suit_char = ''
                                    rank_char = ''
                                    if card_filename[-1].isalpha() and not card_filename[-1].isdigit(): 
                                        suit_char = card_filename[-1]
                                        rank_char = card_filename[:-1]
                                    elif card_filename[0].isalpha() and not card_filename[0].isdigit(): 
                                        suit_char = card_filename[0]
                                        rank_char = card_filename[1:]
                                    
                                    if suit_char and rank_char:
                                        suit_map = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
                                        card_str = rank_char.upper() + suit_map.get(suit_char.lower(), suit_char)
                        
                        if card_str != "N/A":
                            player_info['cards'].append(card_str)
            else: 
                cards_holder_other = player_element.find('div', class_='cards-holder-other-hidden')
                if cards_holder_other:
                    card_images = cards_holder_other.find_all('img', class_='card-image')
                    if card_images: 
                        player_info['has_hidden_cards'] = True
            
            self.player_data.append(player_info)
        return self.player_data
