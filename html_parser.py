from bs4 import BeautifulSoup
import re
import logging # Added import

class PokerPageParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__) # Added logger
        self.soup = None # Initialize soup as None, will be set in parse_html
        self.table_data = {}
        self.player_data = []

    def _check_visibility_of_element_and_its_ancestors(self, element, stop_ancestor):
        # Returns True if element is considered visible, False otherwise.
        # An element is visible if:
        # 1. It exists.
        # 2. It does not have 'pt-hidden' or 'pt-visibility-hidden' class.
        # 3. None of its ancestors up to (but not including) stop_ancestor's parent,
        #    and not stop_ancestor itself if stop_ancestor is one of its direct parents,
        #    have 'pt-hidden' or 'pt-visibility-hidden'.
        if not element: 
            return False
        
        element_classes = element.get('class', [])
        if 'pt-hidden' in element_classes or 'pt-visibility-hidden' in element_classes:
            return False

        parent = element.parent
        while parent and parent != stop_ancestor and parent.name != 'body':
            parent_classes = parent.get('class', [])
            if 'pt-hidden' in parent_classes or 'pt-visibility-hidden' in parent_classes:
                return False # Parent is hidden
            parent = parent.parent
        return True

    def parse_html(self, html_content):
        if not html_content or not html_content.strip():
            self.logger.error("HTML content is empty in PokerPageParser.parse_html") # Replaced print with self.logger.error
            # Return a structure indicating an error or empty state
            return {
                'table_data': {},
                'all_players_data': [],
                'my_player_data': None,
                'error': "Empty or invalid HTML content received"
            }

        self.soup = BeautifulSoup(html_content, 'html.parser')
        # Reset data for the current parse operation
        self.table_data = {}
        self.player_data = []

        table_info = self.analyze_table()
        players_info = self.analyze_players()

        my_player_info = None
        for p_info in players_info:
            if p_info.get('is_my_player'):
                my_player_info = p_info
                break
        
        return {
            'table_data': table_info,
            'all_players_data': players_info,
            'my_player_data': my_player_info
        }

    def analyze_table(self):
        # Ensure soup is available
        if not self.soup:
            self.logger.error("BeautifulSoup object (self.soup) not initialized before calling analyze_table.") # Replaced print with self.logger.error
            return {}
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
            
        # IMPROVED DEALER POSITION DETECTION
        self.table_data['dealer_position'] = "N/A"
        
        # Look for visible dealer buttons in game-position divs
        game_positions = self.soup.find_all('div', class_=re.compile(r'game-position-\d+'))
        for game_pos in game_positions:
            # Skip if the game-position itself is hidden
            if 'pt-visibility-hidden' in game_pos.get('class', []):
                continue
                
            # Look for dealer button that is NOT hidden
            dealer_btn = game_pos.find('div', class_='dealer')
            if dealer_btn and 'pt-visibility-hidden' not in dealer_btn.get('class', []):
                # Extract seat number from game-position class
                game_pos_classes = game_pos.get('class', [])
                for class_name in game_pos_classes:
                    match = re.match(r'game-position-(\d+)', class_name)
                    if match:
                        dealer_seat = match.group(1)
                        self.table_data['dealer_position'] = dealer_seat
                        self.logger.info(f"Found visible dealer button at seat {dealer_seat}")
                        break
                break
        
        # Fallback: original method if no dealer found
        if self.table_data['dealer_position'] == "N/A":
            dealer_buttons = self.soup.find_all('div', class_='dealer', id=re.compile(r'dealer-seat-\d+$'))
            for btn in dealer_buttons:
                parent_game_pos = btn.find_parent('div', class_=re.compile(r'game-position-'))
                is_hidden = 'pt-visibility-hidden' in btn.get('class', [])
                if parent_game_pos and 'pt-visibility-hidden' in parent_game_pos.get('class', []):
                    is_hidden = True
                
                if not is_hidden:
                    dealer_id = btn.get('id', '')
                    if 'dealer-seat-' in dealer_id:
                        # Extract the number from dealer-seat-X and map it to actual seat
                        # The pattern seems to be: dealer-seat-X where X might not directly correspond to seat number
                        # Let's check the parent game-position to get the actual seat
                        if parent_game_pos:
                            parent_classes = parent_game_pos.get('class', [])
                            for class_name in parent_classes:
                                pos_match = re.match(r'game-position-(\d+)', class_name)
                                if pos_match:
                                    self.table_data['dealer_position'] = pos_match.group(1)
                                    self.logger.info(f"Found dealer position via fallback method: seat {pos_match.group(1)}")
                                    break
                        if self.table_data['dealer_position'] != "N/A":
                            break
        
        return self.table_data

    def analyze_players(self):
        # Ensure soup is available
        if not self.soup:
            self.logger.error("BeautifulSoup object (self.soup) not initialized before calling analyze_players.")
            return []
        self.player_data = [] 
        active_player_already_identified_for_this_parse = False

        # Find all elements that are marked as player areas
        player_area_elements = self.soup.find_all('div', class_='player-area')
        self.logger.info(f"Found {len(player_area_elements)} 'div.player-area' elements to process.")

        if not player_area_elements:
            self.logger.warning("No 'div.player-area' elements found. No players will be parsed.")
            return []
        
        for player_element in player_area_elements:
            player_info = {
                'seat': None, 'name': 'N/A', 'stack': 'N/A', 'bet': '0', 
                'is_my_player': False, 'is_empty': False, 'cards': [], 
                'has_turn': False,
                'has_hidden_cards': False
            }

            # Try to extract seat number from the player_element's classes
            element_classes = player_element.get('class', [])
            seat_match = None
            for c_name in element_classes:
                match = re.match(r'player-seat-(\d+)', c_name)
                if match:
                    seat_match = match
                    break
            
            if seat_match:
                player_info['seat'] = seat_match.group(1)
                player_info['id'] = player_info['seat']
            else:
                # Fallback: try to find seat number in parent elements or ID attributes
                seat_found = False
                
                # Check for seat in ID attribute
                element_id = player_element.get('id', '')
                id_match = re.search(r'seat-(\d+)', element_id)
                if id_match:
                    player_info['seat'] = id_match.group(1)
                    player_info['id'] = player_info['seat']
                    seat_found = True
                    self.logger.debug(f"Found seat number {player_info['seat']} in element ID: {element_id}")
                
                # Check for seat in nested elements
                if not seat_found:
                    seat_elements = player_element.find_all(attrs={'class': re.compile(r'seat-\d+')})
                    for seat_el in seat_elements:
                        seat_classes = seat_el.get('class', [])
                        for class_name in seat_classes:
                            seat_match_nested = re.search(r'seat-(\d+)', class_name)
                            if seat_match_nested:
                                player_info['seat'] = seat_match_nested.group(1)
                                player_info['id'] = player_info['seat']
                                seat_found = True
                                self.logger.debug(f"Found seat number {player_info['seat']} in nested element class: {class_name}")
                                break
                        if seat_found:
                            break

            # Check if it's 'my-player'
            if 'my-player' in element_classes:
                player_info['is_my_player'] = True
            
            # Check for empty seat
            empty_seat_element = player_element.find('div', class_='empty-seat')
            if empty_seat_element and empty_seat_element.text.strip().lower() == 'empty':
                player_info['is_empty'] = True
                # For empty seats, try harder to find seat number if not found yet
                if not player_info['seat']:
                    # Look for seat number in the empty seat text or surrounding elements
                    empty_text = empty_seat_element.text.strip()
                    seat_in_text = re.search(r'seat\s*(\d+)', empty_text, re.IGNORECASE)
                    if seat_in_text:
                        player_info['seat'] = seat_in_text.group(1)
                        player_info['id'] = player_info['seat']
                        self.logger.debug(f"Found seat number {player_info['seat']} in empty seat text: {empty_text}")
                
                self.logger.debug(f"Identified as empty seat. Seat: {player_info['seat']}, Classes: {element_classes}")
                self.player_data.append(player_info)
                continue

            # If we still don't have a seat number, assign a temporary one based on position in the list
            if not player_info['seat']:
                temp_seat = str(len(self.player_data) + 1)
                player_info['seat'] = temp_seat
                player_info['id'] = temp_seat
                self.logger.warning(f"No seat number found for non-empty player. Assigned temporary seat: {temp_seat}")

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
                        current_name_text = name_element.text.strip()
                        if "Time:" not in current_name_text:
                            player_info['name'] = current_name_text

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
            
            current_player_meets_active_criteria = False
            
            table_player_div = player_element.find('div', class_='table-player')
            if table_player_div and 'player-active' in table_player_div.get('class', []):
                current_player_meets_active_criteria = True
            
            if not current_player_meets_active_criteria:
                nameplate_div = player_element.find('div', class_='player-nameplate')
                if nameplate_div:
                    countdown_div = nameplate_div.find('div', class_='text-countdown')
                    if self._check_visibility_of_element_and_its_ancestors(countdown_div, nameplate_div):
                        current_player_meets_active_criteria = True
                    
                    if not current_player_meets_active_criteria: 
                        timeout_wrapper_div = nameplate_div.find('div', class_='timeout-wrapper')
                        if self._check_visibility_of_element_and_its_ancestors(timeout_wrapper_div, nameplate_div):
                            current_player_meets_active_criteria = True
            
            if current_player_meets_active_criteria:
                if not active_player_already_identified_for_this_parse:
                    player_info['has_turn'] = True
                    active_player_already_identified_for_this_parse = True
                else:
                    player_info['has_turn'] = False 
                    self.logger.warning(
                        f"Player {player_info.get('name', player_info.get('seat', 'UnknownSeat'))} "
                        f"met active criteria, but another player was already identified as active."
                    )

            if player_info['is_my_player']:
                player_info['available_actions'] = []
                player_info['is_all_in_call_available'] = False
                player_info['bet_to_call'] = 0

                actions_area_wrapper = self.soup.find('div', class_='table-actions-wrapper')
                actions_area = None
                if actions_area_wrapper:
                    actions_area = actions_area_wrapper.find('div', class_='actions-area')
                
                if not actions_area:
                    self.logger.warning("Could not find actions area for my player.")
                else:
                    self.logger.info("Found actions area. Analyzing buttons...")
                    elements_to_check = actions_area.find_all('div', class_=re.compile(r'action-button'), recursive=False)
                    if not elements_to_check:
                        elements_to_check = actions_area.find_all('div', class_=re.compile(r'action-button'))

                    self.logger.info(f"Found {len(elements_to_check)} potential action elements.")

                    unique_actions_found = set()

                    for el in elements_to_check:
                        el_classes = el.get('class', [])
                        is_hidden = 'pt-hidden' in el_classes or 'pt-visibility-hidden' in el_classes
                        is_disabled = 'disabled' in el_classes or el.has_attr('disabled')

                        button_text_parts = [s.lower() for s in el.stripped_strings]
                        button_text_content = " ".join(button_text_parts).strip()
                        
                        if not button_text_content:
                            self.logger.debug(f"Skipping element, no button text could be extracted: {el.name} {el_classes}")
                            continue

                        self.logger.debug(f"Processing button: '{button_text_content}'")

                        current_element_action_amount = 0.0
                        amount_span = el.find('span', class_='action-value')
                        if amount_span and amount_span.text.strip():
                            amount_text = amount_span.text.strip()
                            self.logger.debug(f"Found amount span: '{amount_text}'")
                            try:
                                text_to_parse = amount_text.replace('€', '').replace('$', '').strip()
                                text_to_parse = text_to_parse.replace(',', '.')
                                cleaned_amount_text = re.sub(r'[^\d\.]', '', text_to_parse)
                                
                                if cleaned_amount_text:
                                    if cleaned_amount_text.count('.') > 1:
                                        parts = cleaned_amount_text.split('.')
                                        if len(parts) > 1 and parts[0].isdigit() and parts[1].isdigit():
                                            cleaned_amount_text = f"{parts[0]}.{parts[1]}"
                                        else:
                                            raise ValueError(f"Multiple decimal points: {cleaned_amount_text}")
                                    
                                    current_element_action_amount = float(cleaned_amount_text)
                                    self.logger.debug(f"Parsed amount: {current_element_action_amount}")
                            except ValueError as e:
                                self.logger.warning(f"Could not parse amount: '{amount_text}'. Error: {e}")
                        else:
                            amount_el_fallback = el.find(class_='table-action-button__amount')
                            if amount_el_fallback and amount_el_fallback.text.strip():
                                amount_text_fallback = amount_el_fallback.text.strip()
                                try:
                                    text_to_parse_fallback = amount_text_fallback.replace('€', '').replace('$', '').strip()
                                    text_to_parse_fallback = text_to_parse_fallback.replace(',', '.')
                                    cleaned_amount_text_fallback = re.sub(r'[^\d\.]', '', text_to_parse_fallback)

                                    if cleaned_amount_text_fallback:
                                        if cleaned_amount_text_fallback.count('.') > 1:
                                            parts_fallback = cleaned_amount_text_fallback.split('.')
                                            if len(parts_fallback) > 1 and parts_fallback[0].isdigit() and parts_fallback[1].isdigit():
                                                cleaned_amount_text_fallback = f"{parts_fallback[0]}.{parts_fallback[1]}"
                                        current_element_action_amount = float(cleaned_amount_text_fallback)
                                except ValueError as e:
                                    self.logger.warning(f"Could not parse fallback amount: '{amount_text_fallback}'. Error: {e}")

                        if ('call' in button_text_content or 'all in' in button_text_content):
                            if current_element_action_amount > 0:
                                player_info['bet_to_call'] = current_element_action_amount
                            elif 'call' in button_text_content and current_element_action_amount == 0:
                                if " 0" in button_text_content or " 0.00" in button_text_content : 
                                     player_info['bet_to_call'] = 0.0

                        if is_hidden or is_disabled:
                            continue

                        action_identified = None
                        if 'call' in button_text_content:
                            action_identified = 'call'
                        elif 'raise' in button_text_content:
                            action_identified = 'raise'
                        elif 'fold' in button_text_content:
                            action_identified = 'fold'
                        elif 'all in' in button_text_content:
                            action_identified = 'all_in'
                        elif 'check' in button_text_content:
                            action_identified = 'check'
                        elif 'bet' in button_text_content:
                            action_identified = 'bet'
                        else:
                            self.logger.warning(f"Unrecognized action: '{button_text_content}'")
                        
                        if action_identified and action_identified not in unique_actions_found:
                            player_info['available_actions'].append(action_identified)
                            unique_actions_found.add(action_identified)

                if 'all_in' in player_info['available_actions']:
                    player_info['is_all_in_call_available'] = True
                elif 'call' in player_info['available_actions']:
                    current_stack_str = player_info.get('stack', '0')
                    try:
                        current_stack = float(re.sub(r'[^\d\.\,]', '', current_stack_str).replace(',', '.'))
                        if player_info['bet_to_call'] > 0 and current_stack > 0 and player_info['bet_to_call'] >= current_stack:
                            player_info['is_all_in_call_available'] = True
                    except ValueError:
                        pass

                cards_holder = player_element.find('div', class_='cards-holder-hero')
                if cards_holder:
                    card_divs = cards_holder.find_all('div', class_=re.compile(r'\bcard\d*\b'))
                    processed_cards = set()
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
                                
                                cf = card_filename.upper()
                                parsed_rank_val = None
                                parsed_suit_char_val = None

                                possible_ranks = {"A", "K", "Q", "J", "T", "2", "3", "4", "5", "6", "7", "8", "9", "10"}
                                possible_suit_chars = {"H", "D", "C", "S"}
                                suit_symbol_map = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}

                                if len(cf) == 2:
                                    if cf[0] in possible_ranks and cf[0] != '1' and cf[1] in possible_suit_chars:
                                        parsed_rank_val = cf[0]
                                        parsed_suit_char_val = cf[1]
                                    elif cf[0] in possible_suit_chars and cf[1] in possible_ranks and cf[1] != '1':
                                        parsed_rank_val = cf[1]
                                        parsed_suit_char_val = cf[0]
                                elif len(cf) == 3:
                                    if cf[:2] == "10" and cf[2] in possible_suit_chars:
                                        parsed_rank_val = "10"
                                        parsed_suit_char_val = cf[2]
                                    elif cf[0] in possible_suit_chars and cf[1:] == "10":
                                        parsed_rank_val = "10"
                                        parsed_suit_char_val = cf[0]
                                
                                if parsed_rank_val and parsed_suit_char_val:
                                    final_suit_symbol = suit_symbol_map.get(parsed_suit_char_val)
                                    if final_suit_symbol:
                                        card_str = parsed_rank_val + final_suit_symbol
                        
                        if card_str != "N/A" and card_str not in processed_cards:
                            player_info['cards'].append(card_str)
                            processed_cards.add(card_str)
            else: 
                cards_holder_other = player_element.find('div', class_='cards-holder-other-hidden')
                if cards_holder_other:
                    card_images = cards_holder_other.find_all('img', class_='card-image')
                    if card_images: 
                        player_info['has_hidden_cards'] = True
            
            self.player_data.append(player_info)

        # Log summary of players found
        total_players = len(self.player_data)
        empty_players = len([p for p in self.player_data if p.get('is_empty')])
        active_players_count = total_players - empty_players
        self.logger.info(f"Player detection complete: {total_players} total seats, {active_players_count} active players, {empty_players} empty seats")

        # Log all detected players with their seats
        for p in self.player_data:
            if not p.get('is_empty'):
                self.logger.debug(f"Detected player: {p.get('name', 'N/A')} in seat {p.get('seat')}, is_my_player: {p.get('is_my_player', False)}")

        # --- IMPROVED POSITION CALCULATION ---
        if self.player_data:
            dealer_position = self.table_data.get('dealer_position')
            self.logger.info(f"Using dealer position: {dealer_position}")
            
            if dealer_position and dealer_position != "N/A":
                try:
                    dealer_seat = int(dealer_position)
                    # Get all non-empty players sorted by seat number
                    active_players = [p for p in self.player_data if not p.get('is_empty') and p.get('seat') is not None]
                    
                    # Convert seat to int for sorting, handle any conversion errors
                    valid_active_players = []
                    for p in active_players:
                        try:
                            p['seat_int'] = int(p['seat'])
                            valid_active_players.append(p)
                        except (ValueError, TypeError):
                            self.logger.warning(f"Invalid seat number for player {p.get('name', 'Unknown')}: {p.get('seat')}")
                    
                    active_players = sorted(valid_active_players, key=lambda x: x['seat_int'])
                    num_players = len(active_players)
                    
                    self.logger.info(f"Position calculation: {num_players} active players, dealer at seat {dealer_seat}")
                    
                    if num_players > 0:
                        # Find dealer in active players
                        dealer_idx = -1
                        for i, p in enumerate(active_players):
                            if p['seat_int'] == dealer_seat:
                                dealer_idx = i
                                break
                        
                        if dealer_idx == -1:
                            self.logger.warning(f"Dealer seat {dealer_seat} not found among active players. Using first active player as fallback.")
                            # Fallback: use the first active player as dealer
                            dealer_idx = 0
                            self.logger.info(f"Using player in seat {active_players[0]['seat']} as dealer (fallback)")
                        
                        # Assign positions based on number of players
                        if num_players == 2:
                            # Heads-up: Dealer is SB, other is BB
                            active_players[dealer_idx]['position'] = "SB"
                            active_players[(dealer_idx + 1) % num_players]['position'] = "BB"
                        elif num_players > 2:
                            # Multi-way: assign standard positions
                            active_players[dealer_idx]['position'] = "BTN"
                            active_players[(dealer_idx + 1) % num_players]['position'] = "SB"
                            active_players[(dealer_idx + 2) % num_players]['position'] = "BB"

                            if num_players == 3:
                                pass  # Only BTN, SB, BB
                            elif num_players == 4:
                                active_players[(dealer_idx + 3) % num_players]['position'] = "UTG"
                            elif num_players == 5:
                                active_players[(dealer_idx + 3) % num_players]['position'] = "UTG"
                                active_players[(dealer_idx + 4) % num_players]['position'] = "CO"
                            elif num_players >= 6:
                                active_players[(dealer_idx + 3) % num_players]['position'] = "UTG"
                                co_idx = (dealer_idx - 1 + num_players) % num_players
                                active_players[co_idx]['position'] = "CO"
                                
                                # Assign MP to players between UTG and CO
                                current_idx = (dealer_idx + 4) % num_players
                                while current_idx != co_idx:
                                    if 'position' not in active_players[current_idx]:
                                        active_players[current_idx]['position'] = "MP"
                                    current_idx = (current_idx + 1) % num_players
                                    if current_idx == dealer_idx:  # Safety check
                                        break
                        
                        # Log position assignments
                        for p in active_players:
                            pos = p.get('position', 'Unknown')
                            self.logger.info(f"Player {p.get('name', 'N/A')} in seat {p.get('seat')} assigned position: {pos}")
                    else:
                        self.logger.warning("No valid active players found for position calculation.")
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Error parsing dealer position '{dealer_position}': {e}")
                except Exception as e:
                    self.logger.error(f"Unexpected error during position calculation: {e}", exc_info=True)
            else:
                self.logger.warning("No dealer position available, positions will not be assigned.")
        
        return self.player_data
