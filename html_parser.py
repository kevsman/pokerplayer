from bs4 import BeautifulSoup
import re

class PokerPageParser:
    def __init__(self):
        self.soup = None # Initialize soup as None, will be set in parse_html
        self.table_data = {}
        self.player_data = []

    def parse_html(self, html_content):
        if not html_content or not html_content.strip():
            print("Error: HTML content is empty in PokerPageParser.parse_html")
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
            print("Error: BeautifulSoup object (self.soup) not initialized before calling analyze_table.")
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
        # Ensure soup is available
        if not self.soup:
            print("Error: BeautifulSoup object (self.soup) not initialized before calling analyze_players.")
            return []
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
                    # Check for nameplate name if other methods fail, but exclude countdown timer text
                    elif name_element.text.strip() and name_element.text.strip().lower() != 'empty':
                        # If the name contains "Time:", it's likely part of a countdown timer, so ignore it or find a cleaner name.
                        # This is a basic check; more robust parsing might be needed if "Time:" can legitimately be part of a name.
                        current_name_text = name_element.text.strip()
                        if "Time:" not in current_name_text: # Added check to avoid timer text
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
                player_info['available_actions'] = []
                player_info['is_all_in_call_available'] = False
                player_info['bet_to_call'] = 0 # Initialize

                actions_area_wrapper = self.soup.find('div', class_='table-actions-wrapper')
                actions_area = None
                if actions_area_wrapper:
                    actions_area = actions_area_wrapper.find('div', class_='actions-area')
                
                if not actions_area:
                    print("Could not find actions area ('div.actions-area' inside 'div.table-actions-wrapper'). No actions will be parsed.")
                else:
                    print("Found actions area. Analyzing buttons...")
                    # elements_to_check = actions_area.find_all(lambda tag: tag.name == 'div' and 'action-button' in tag.get('class', []))
                    # Find only direct children that are action buttons to avoid double counting
                    elements_to_check = actions_area.find_all('div', class_=re.compile(r'action-button'), recursive=False)
                    if not elements_to_check: # If no direct children, try a broader search but be wary of duplicates
                        elements_to_check = actions_area.find_all('div', class_=re.compile(r'action-button'))
                        # This broader search might re-introduce duplicates if the HTML is complex.
                        # A more robust solution would involve tracking processed elements or using more specific selectors.
                        # For now, we'll proceed and rely on the available_actions set to prevent functional duplicates.

                    print(f"Found {len(elements_to_check)} potential action elements.")
                    
                    # Use a set to store unique actions to avoid duplicates from parsing
                    unique_actions_found = set()

                    for el in elements_to_check:
                        el_classes = el.get('class', [])
                        is_hidden = 'pt-hidden' in el_classes or 'pt-visibility-hidden' in el_classes
                        is_disabled = 'disabled' in el_classes or el.has_attr('disabled')

                        # Extract text content more robustly
                        button_text_parts = [s.lower() for s in el.stripped_strings]
                        button_text_content = " ".join(button_text_parts).strip()
                        
                        # --- Start of new debug/parsing block ---
                        if not button_text_content:
                            print(f"Skipping element, no button text could be extracted: {el.name} {el_classes}")
                            continue

                        print(f"--- Debug Amount Parsing for element: ---")
                        print(f"Element raw text: '{el.text.strip()}'")
                        print(f"Processed button_text_content: '{button_text_content}'")

                        current_element_action_amount = 0.0
                        # Try to find amount in <span class="action-value">
                        amount_span = el.find('span', class_='action-value')
                        if amount_span and amount_span.text.strip():
                            amount_text = amount_span.text.strip()
                            print(f"Found amount span <span class='action-value'>: '{amount_text}'")
                            try:
                                # Remove currency symbols and leading/trailing whitespace
                                text_to_parse = amount_text.replace('€', '').replace('$', '').strip()
                                # Replace comma with period for European-style decimals
                                text_to_parse = text_to_parse.replace(',', '.')
                                # At this point, text_to_parse should be like "0.40"
                                # Keep only digits and the decimal point.
                                cleaned_amount_text = re.sub(r'[^\d\.]', '', text_to_parse) # Corrected regex
                                
                                if cleaned_amount_text:
                                    # Ensure there's at most one decimal point
                                    if cleaned_amount_text.count('.') > 1:
                                        # Handle cases like "..40" or "0.4.0" by trying to split and take valid part
                                        parts = cleaned_amount_text.split('.')
                                        if len(parts) > 1 and parts[0].isdigit() and parts[1].isdigit():
                                            cleaned_amount_text = f"{parts[0]}.{parts[1]}"
                                        else: # Invalid format after multiple dots
                                            raise ValueError(f"Multiple decimal points in cleaned text: {cleaned_amount_text}")
                                    
                                    current_element_action_amount = float(cleaned_amount_text)
                                    print(f"Parsed amount from span: {current_element_action_amount}")
                                else:
                                    print(f"Amount text became empty after cleaning: '{amount_text}' -> '{text_to_parse}'")
                            except ValueError as e:
                                print(f"Could not parse amount from span text: '{amount_text}'. Cleaned: '{cleaned_amount_text}'. Error: {e}")
                        else:
                            # Fallback for table-action-button__amount (older structure or different HTML)
                            amount_el_fallback = el.find(class_='table-action-button__amount')
                            if amount_el_fallback and amount_el_fallback.text.strip():
                                amount_text_fallback = amount_el_fallback.text.strip()
                                print(f"Found fallback amount element <... class='table-action-button__amount'>: '{amount_text_fallback}'")
                                try:
                                    text_to_parse_fallback = amount_text_fallback.replace('€', '').replace('$', '').strip()
                                    text_to_parse_fallback = text_to_parse_fallback.replace(',', '.')
                                    cleaned_amount_text_fallback = re.sub(r'[^\d\.]', '', text_to_parse_fallback) # Corrected regex

                                    if cleaned_amount_text_fallback:
                                        if cleaned_amount_text_fallback.count('.') > 1:
                                            parts_fallback = cleaned_amount_text_fallback.split('.')
                                            if len(parts_fallback) > 1 and parts_fallback[0].isdigit() and parts_fallback[1].isdigit():
                                                cleaned_amount_text_fallback = f"{parts_fallback[0]}.{parts_fallback[1]}"
                                            else:
                                                raise ValueError(f"Multiple decimal points in cleaned fallback text: {cleaned_amount_text_fallback}")
                                        current_element_action_amount = float(cleaned_amount_text_fallback)
                                        print(f"Parsed amount from fallback: {current_element_action_amount}")
                                    else:
                                        print(f"Fallback amount text became empty after cleaning: '{amount_text_fallback}' -> '{text_to_parse_fallback}'")
                                except ValueError as e:
                                    print(f"Could not parse amount from fallback text: '{amount_text_fallback}'. Cleaned: '{cleaned_amount_text_fallback}'. Error: {e}")

                        # Update player_info['bet_to_call'] based on parsed amount and action type
                        if ('call' in button_text_content or 'all in' in button_text_content):
                            if current_element_action_amount > 0:
                                player_info['bet_to_call'] = current_element_action_amount
                                print(f"Updated player_info['bet_to_call'] to {player_info['bet_to_call']} from button '{button_text_content}' with amount {current_element_action_amount}")
                            elif 'call' in button_text_content and current_element_action_amount == 0:
                                if " 0" in button_text_content or " 0.00" in button_text_content : 
                                     player_info['bet_to_call'] = 0.0
                                     print(f"Button is 'Call 0', setting player_info['bet_to_call'] to 0.0")
                                else:
                                     print(f"INFO: 'call' action found, but amount parsed from button is 0 (and not explicitly 'Call 0'). player_info['bet_to_call'] ({player_info.get('bet_to_call', 0)}) not updated by this button. This might require opponent's bet data.")
                        
                        print(f"Player info bet_to_call after this element's logic: {player_info.get('bet_to_call', 0)}")
                        print(f"--- End Debug Amount Parsing ---")
                        # --- End of new debug/parsing block ---

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
                            print(f"Unrecognized action button text: '{button_text_content}'")
                        
                        if action_identified and action_identified not in unique_actions_found:
                            player_info['available_actions'].append(action_identified)
                            unique_actions_found.add(action_identified)
                        elif action_identified:
                            print(f"Action '{action_identified}' already processed for this player. Text: '{button_text_content}'")


                # After iterating through all buttons, determine is_all_in_call_available
                if 'all_in' in player_info['available_actions']:
                    player_info['is_all_in_call_available'] = True
                elif 'call' in player_info['available_actions']:
                    current_stack_str = player_info.get('stack', '0')
                    current_stack = 0
                    try:
                        current_stack = float(re.sub(r'[^\d\.\,]', '', current_stack_str).replace(',', '.'))
                    except ValueError:
                        pass # current_stack remains 0
                    
                    # If the amount to call (derived from buttons) is greater or equal to stack
                    if player_info['bet_to_call'] > 0 and current_stack > 0 and player_info['bet_to_call'] >= current_stack:
                        player_info['is_all_in_call_available'] = True
                
                # Debug prints after all processing for the player
                print(f"Final detected actions for player {player_info.get('name', 'N/A')}: {player_info['available_actions']}")
                print(f"Is all-in call available for player {player_info.get('name', 'N/A')}: {player_info['is_all_in_call_available']}")
                print(f"Player's bet_to_call: {player_info['bet_to_call']}")

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
        return self.player_data
