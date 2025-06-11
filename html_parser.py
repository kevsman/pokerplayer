from bs4 import BeautifulSoup
import re
import logging # Added import

class PokerPageParser:
    def __init__(self, logger, config): # Add logger and config
        self.logger = logger # Use passed logger
        self.config = config # Store config
        self.soup = None # Initialize soup as None, will be set in parse_html
        self.table_data = {}
        self.player_data = []
        self.last_parsed_actions = [] # To store actions from the most recent parse

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
            self.logger.error("HTML content is empty in PokerPageParser.parse_html")
            return {
                'table_data': {},
                'all_players_data': [],
                'my_player_data': None,
                'error': "Empty or invalid HTML content received",
                'parsed_actions': [] # Ensure parsed_actions is returned even on error
            }

        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.table_data = {}
        self.player_data = []
        
        # Ensure this is cleared at the start of a full parse
        self.last_parsed_actions = []

        # These methods should populate self.table_data and self.player_data
        # For example:
        # self._parse_table_info() # Populates self.table_data (including game_stage)
        # self._parse_player_data_elements() # Finds player elements
        # self.analyze_players() # Populates self.player_data with detailed info for each player
                                 # (name, seat, stack, cards, bet_this_street, is_folded, is_all_in, position)
        # self.analyze_community_cards() # Populates community cards in self.table_data

        # Critical: Ensure analyze_players (or equivalent) populates self.player_data thoroughly
        # *before* calling _update_last_parsed_actions.
        # The old heuristic in analyze_players for adding "BET" actions to self.last_parsed_actions
        # should be removed as _update_last_parsed_actions handles this more comprehensively.

        # After self.player_data and self.table_data are populated:
        self._update_last_parsed_actions()

        # parse_html likely returns a summary of game state or status
        # For example:
        # return {
        #     'status': 'success',
        #     'hand_id': self.table_data.get('hand_id'),
        #     'game_stage': self.table_data.get('game_stage'),
        #     'warnings': self.warnings_log # if you have one
        # }
        # The exact return value depends on how it's used by PokerBot.
        # For now, just ensuring the call is made.
        # ... existing return ...

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
        if not self.soup:
            self.logger.error("BeautifulSoup object (self.soup) not initialized before calling analyze_players.")
            return []
        self.player_data = [] 
        
        current_street_for_action_parsing = self.table_data.get('game_stage', 'preflop').lower()
        
        potential_active_players = []


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
                    
                    # Try to parse this bet as an action for history if it seems like a new bet
                    try:
                        bet_value = self.parse_monetary_value(player_info['bet'])
                        # Get the player's previous bet amount from the main player_data list if available
                        # This requires that self.player_data from the *previous* parse cycle is accessible
                        # or that we store a "last known bet" for each player.
                        # For now, this simplistic approach will create an action for any displayed bet.
                        # Refinement: Only log if this bet_value is different from a previously known bet for this player this street.

                        if bet_value > 0 and not player_info['is_my_player']:
                            # Basic check: if player has a bet amount and wasn't the one who just acted (bot),
                            # it's potentially a new action.
                            # More robust: Compare current bet to previous bet on this street.
                            # If no previous bet, it's a BET. If previous bet < current bet, it's a RAISE.
                            # This requires tracking previous bet amounts per player per street.

                            # Placeholder for previous bet tracking - assume 0 for now for simplicity
                            previous_bet_on_street = 0 
                            action_type = "BET"
                            if bet_value > previous_bet_on_street:
                                # This logic is too simple. A player calling a bet will also have bet_value > 0.
                                # A true RAISE means they put in more than the current highest bet.
                                # A BET means they are the first to put money in on this street (or opening a new betting round).
                                # A CALL means they match the current highest bet.
                                # This heuristic needs significant improvement.
                                # For now, let's assume any new bet amount from an opponent is a "BET"
                                # and rely on PokerBot's deduplication and future DecisionEngine logic.
                                pass # Keeping it simple as "BET" for now.

                            opponent_action = {
                                "player_id": player_info.get('name', player_info.get('seat', 'UnknownOpponent')),
                                "action_type": action_type, # Defaulting to BET, needs refinement
                                "amount": bet_value,
                                "street": current_street_for_action_parsing,
                                "is_bot": False,
                                "position": player_info.get('position', 'unknown'), # Add position
                                # sequence will be added by PokerBot
                            }
                            # Add to self.last_parsed_actions - deduplication should happen in PokerBot
                            self.last_parsed_actions.append(opponent_action)
                            self.logger.debug(f"Parsed potential opponent action from bet field: {opponent_action}")

                    except ValueError:
                        self.logger.warning(f"Could not parse bet value {player_info['bet']} for action history.")


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
                potential_active_players.append(player_info)


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

        # New logic to handle 'has_turn' based on collected potential_active_players
        if not potential_active_players:
            self.logger.info("No player identified as active in this parse.")
            # Explicitly set table_data['active_player_name'] to "N/A" if no one is active
            if hasattr(self, 'table_data') and isinstance(self.table_data, dict):
                 self.table_data['active_player_name'] = "N/A"
        elif len(potential_active_players) == 1:
            active_player_info = potential_active_players[0]
            active_player_info['has_turn'] = True
            self.logger.info(f"Successfully identified active player: {active_player_info.get('name', active_player_info.get('seat', 'UnknownSeat'))}")
            # Update table_data with the active player's name
            if hasattr(self, 'table_data') and isinstance(self.table_data, dict):
                self.table_data['active_player_name'] = active_player_info.get('name', 'N/A')

            # Ensure other players are marked as not having the turn
            for p_info in self.player_data:
                if p_info is not active_player_info:
                    p_info['has_turn'] = False
        else: # Multiple players identified as active
            self.logger.warning(f"Multiple players ({len(potential_active_players)}) identified as active. This should not happen. Listing them:")
            for i, p_info in enumerate(potential_active_players):
                self.logger.warning(f"  Potential active player {i+1}: {p_info.get('name', p_info.get('seat', 'UnknownSeat'))}")
                p_info['has_turn'] = False # Mark all as false to avoid incorrect state downstream
            # Set table_data['active_player_name'] to "Error" or "Multiple" to indicate problem
            if hasattr(self, 'table_data') and isinstance(self.table_data, dict):
                self.table_data['active_player_name'] = "Error: Multiple Active"


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

    def get_player_position(self, seat_number_str, total_players):
        # ... (implementation of get_player_position)
        # This is a placeholder. Actual implementation would depend on how seats are numbered
        # and how dealer button is identified.
        # Example:
        # dealer_seat_str = self.table_data.get('dealer_position')
        # if not dealer_seat_str or not seat_number_str:
        #     return "Unknown"
        # try:
        #     dealer_seat = int(dealer_seat_str)
        #     my_seat = int(seat_number_str)
        #     # Calculate relative position based on dealer, total_players, and my_seat
        #     # ... logic for SB, BB, UTG, MP, CO, BTN ...
        #     return "CalculatedPosition"
        # except ValueError:
        #     return "Unknown"
        self.logger.debug(f"Placeholder get_player_position called for seat {seat_number_str}, total {total_players}")
        return f"Pos_S{seat_number_str}" # Simple placeholder


    def parse_monetary_value(self, value_str):
        if value_str is None:
            return 0.0
        if isinstance(value_str, (int, float)):
            return float(value_str)
        
        # Remove currency symbols and spaces, replace comma with dot for decimal
        cleaned_str = str(value_str).replace('€', '').replace('$', '').replace(' ', '')
        
        # Handle cases like "1.234,56" (German) -> "1234.56"
        if ',' in cleaned_str and '.' in cleaned_str:
            if cleaned_str.rfind('.') < cleaned_str.rfind(','): # Comma is decimal separator
                cleaned_str = cleaned_str.replace('.', '') # Remove thousand separator
                cleaned_str = cleaned_str.replace(',', '.') # Replace comma with dot
        elif ',' in cleaned_str: # Only comma present, assume it's decimal
             cleaned_str = cleaned_str.replace(',', '.')
        
        # Remove any remaining non-numeric characters except the decimal point
        # cleaned_str = re.sub(r'[^\\d\\.]', '', cleaned_str) # This might be too aggressive if there are other valid formats

        try:
            return float(cleaned_str)
        except ValueError:
            self.logger.warning(f"Could not parse monetary value: '{value_str}' (cleaned: '{cleaned_str}')")
            return 0.0

    def get_parsed_actions(self, html_content_for_reparse=None):
        """
        Returns the actions parsed during the last call to parse_html.
        If html_content_for_reparse is provided, it will re-parse that content
        and return actions from it.
        """
        if html_content_for_reparse:
            self.logger.debug("get_parsed_actions called with html_content_for_reparse.")
            # Store original state (parser's internal state like soup, hand_id, game_stage, etc.)
            original_soup = self.soup
            original_hand_id = getattr(self, 'hand_id', None)
            original_game_stage = getattr(self, 'game_stage', None)
            # Potentially other state like self.player_data, self.table_data if they are not fully reset/rebuilt by parse_html
            
            # It's crucial that if parse_html is called here, it correctly rebuilds all necessary
            # intermediate state (like self.player_data, self.table_data) that _update_last_parsed_actions depends on.
            try:
                self.parse_html(html_content_for_reparse) # This will call _update_last_parsed_actions
            finally:
                # Restore original state
                self.soup = original_soup
                if hasattr(self, 'hand_id'): # Check if attribute exists before setting
                    self.hand_id = original_hand_id
                if hasattr(self, 'game_stage'): # Check if attribute exists
                    self.game_stage = original_game_stage
                # If parse_html modified self.player_data and self.table_data, and they are part of the "main" state
                # of the parser instance, they might need restoration if get_parsed_actions is meant to be side-effect-free
                # on the main parser state. However, the current bot loop calls parse_html then get_parsed_actions
                # with the same HTML, so this re-parse might be redundant if the main state is already up-to-date.
                # For now, following the pattern of re-parsing and restoring key attributes.
        else:
            # If no HTML for re-parse, assume parse_html was called before and self.last_parsed_actions is current.
            # However, to be safe and ensure it's always based on the latest call context if parse_html isn't
            # guaranteed to have been called immediately prior with the exact same state:
            # self._update_last_parsed_actions() # This would re-evaluate based on current self.player_data/table_data
            # Given the bot's usage pattern, this 'else' branch might not be hit if current_html is always passed.
            self.logger.debug("get_parsed_actions called without html_content_for_reparse. Using existing last_parsed_actions.")


        return list(self.last_parsed_actions) # Return a copy

    def _update_last_parsed_actions(self):
        """
        Infers actions for each opponent based on the current game state.
        This method should be called after self.player_data and self.table_data are populated.
        It populates self.last_parsed_actions.
        """
        self.last_parsed_actions = []  # Clear any previous actions

        if not self.player_data or not self.table_data:
            self.logger.warning("Cannot update last_parsed_actions: player_data or table_data missing.")
            return

        current_street = self.table_data.get('game_stage', 'unknown').lower()
        if current_street == 'unknown' or not current_street:
            self.logger.warning("Cannot determine current street for parsing actions.")
            return

        bot_player_name = self.config.get('bot_player_name')
        if not bot_player_name:
            # Fallback or log error if bot_player_name is crucial and not set
            self.logger.warning("Bot player name not configured; skipping self-exclusion in action parsing.")


        for p_data in self.player_data:
            player_name = p_data.get('name')

            if p_data.get('is_empty'):
                continue
            if bot_player_name and player_name == bot_player_name: # Skip the bot itself
                continue
            if not player_name: # Skip if no player name
                self.logger.debug("Skipping player with no name in action parsing.")
                continue

            position = p_data.get('position')
            if not position:
                # Attempt to derive position if missing, or log a warning
                raw_seat = p_data.get('seat')
                num_players_for_pos_calc = len([p for p in self.player_data if not p.get('is_empty')])
                if hasattr(self, 'get_player_position') and callable(getattr(self, 'get_player_position')) and raw_seat is not None:
                    position = self.get_player_position(raw_seat, num_players_for_pos_calc)
                else:
                    position = f"Seat_{raw_seat}" if raw_seat is not None else "unknown"
                self.logger.debug(f"Position for player {player_name} was missing, derived/set to: {position}")


            # Crucial: 'bet' should be player's committed chips *this street*.
            player_bet_this_street = self.parse_monetary_value(p_data.get('bet', '0'))
            is_folded = p_data.get('is_folded', False)
            is_all_in = p_data.get('is_all_in', False) # Assumes parser can determine this

            action_type = None
            amount = 0.0

            if is_folded:
                action_type = "FOLD"
                amount = 0.0
            else:
                # Calculate highest bet made by *other* active (not folded) players this street
                highest_bet_by_others_this_street = 0.0
                active_bets_by_others = []
                for other_p_data in self.player_data:
                    if other_p_data.get('is_empty') or other_p_data.get('name') == player_name:
                        continue
                    if not other_p_data.get('is_folded'):
                        other_bet_val = self.parse_monetary_value(other_p_data.get('bet', '0'))
                        active_bets_by_others.append(other_bet_val)
                
                if active_bets_by_others:
                    highest_bet_by_others_this_street = max(active_bets_by_others)
                
                if player_bet_this_street > 0:
                    if player_bet_this_street > highest_bet_by_others_this_street:
                        if highest_bet_by_others_this_street > 0:
                            action_type = "RAISE"
                        else:
                            action_type = "BET"
                        amount = player_bet_this_street
                    elif player_bet_this_street == highest_bet_by_others_this_street:
                        # This implies player_bet_this_street > 0 due to outer if-condition
                        action_type = "CALL"
                        amount = player_bet_this_street
                    else: # player_bet_this_street < highest_bet_by_others_this_street
                        if is_all_in:
                            action_type = "CALL" # All-in call for less
                            amount = player_bet_this_street
                        else:
                            self.logger.debug(f"Player {player_name} has bet {player_bet_this_street} which is less than highest other bet {highest_bet_by_others_this_street} and not marked all-in. No action parsed for this state.")
                            pass # Or potentially log warning, this state might be mid-action or inconsistent
                else: # player_bet_this_street == 0
                    if highest_bet_by_others_this_street == 0:
                        action_type = "CHECK"
                        amount = 0.0
                    else:
                        # Player is facing a bet (highest_bet_by_others_this_street > 0) but has 0 committed.
                        # This means they haven't acted yet on this bet, or they will fold (which is handled by is_folded).
                        # No action to record for them in this state unless it's their turn and they are deciding.
                        # The parser identifies the outcome of an action.
                        pass

            if action_type:
                action_entry = {
                    'player_id': player_name, # Ensure this is the consistent player identifier
                    'action_type': action_type,
                    'amount': float(amount),
                    'street': current_street,
                    'position': position,
                    'is_bot': False # Parsed actions are for opponents
                }
                self.last_parsed_actions.append(action_entry)
                self.logger.debug(f"Parser inferred action for {player_name}: {action_entry}")
        
        self.logger.debug(f"Final last_parsed_actions for this cycle: {self.last_parsed_actions}")
