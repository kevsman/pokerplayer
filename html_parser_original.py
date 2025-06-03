from bs4 import BeautifulSoup
import re
import logging # Added import

# Import the enhanced position calculator
try:
    from position_calculator import calculate_positions
except ImportError:
    calculate_positions = None # Will fall back to internal calculation if import fails

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
        
    def _calculate_positions_internal(self):
        """
        Calculate poker player positions based on dealer position.
        This is an internal fallback implementation if position_calculator fails.
        """
        try:
            dealer_seat = int(self.table_data['dealer_position'])
            self.logger.info(f"Internal position calculation starting with dealer_seat: {dealer_seat}")
            
            # Log raw player data for debugging
            self.logger.info(f"Raw player data before position calculation:")
            for p in self.player_data:
                self.logger.info(f"  Seat: {p.get('seat', 'N/A')}, "
                               f"Name: {p.get('name', 'N/A')}, "
                               f"Is My Player: {p.get('is_my_player', False)}, "
                               f"Is Empty: {p.get('is_empty', False)}")
            
            # Filter and sort active (non-empty) players by seat number
            active_players = sorted(
                [p for p in self.player_data if not p.get('is_empty') and p.get('seat') is not None],
                key=lambda x: int(x['seat'])
            )
            
            # Log active players after sorting
            self.logger.info(f"Active players after sorting (total: {len(active_players)}):")
            for i, p in enumerate(active_players):
                self.logger.info(f"  Index: {i}, Seat: {p.get('seat')}, "
                               f"Name: {p.get('name', 'N/A')}, "
                               f"Is My Player: {p.get('is_my_player', False)}")
                               
            num_players = len(active_players)
            if num_players == 0:
                self.logger.warning("No active players found to assign positions.")
                return
            
            # Find dealer's index in the sorted active players list
            dealer_idx = -1
            for i, p in enumerate(active_players):
                if int(p['seat']) == dealer_seat:
                    dealer_idx = i
                    break
            
            if dealer_idx == -1:
                self.logger.warning(f"Dealer seat {dealer_seat} not found among active players.")
                return
            
            self.logger.info(f"Found dealer at index: {dealer_idx} in the sorted players list")
            
            # Clear out any existing position data
            for player in active_players:
                if 'position' in player:
                    del player['position']
            
            # Assign positions based on the number of players
            if num_players == 2:  # Heads-up
                self.logger.info("Assigning positions for 2-player game (heads-up)")
                # In heads-up, dealer is SB and other player is BB
                active_players[dealer_idx]['position'] = "SB"
                active_players[(dealer_idx + 1) % num_players]['position'] = "BB"
                
                self.logger.info(f"  SB (Dealer): Player at seat {active_players[dealer_idx].get('seat')}")
                self.logger.info(f"  BB: Player at seat {active_players[(dealer_idx + 1) % num_players].get('seat')}")
                
            elif num_players > 2:  # 3+ players
                self.logger.info(f"Assigning positions for {num_players}-player game")
                
                # Standard positions: BTN (dealer), SB, BB
                active_players[dealer_idx]['position'] = "BTN"
                sb_idx = (dealer_idx + 1) % num_players
                bb_idx = (dealer_idx + 2) % num_players
                
                active_players[sb_idx]['position'] = "SB"
                active_players[bb_idx]['position'] = "BB"
                
                self.logger.info(f"  BTN (Dealer): Player at seat {active_players[dealer_idx].get('seat')}")
                self.logger.info(f"  SB: Player at seat {active_players[sb_idx].get('seat')}")
                self.logger.info(f"  BB: Player at seat {active_players[bb_idx].get('seat')}")
                
                # Assign remaining positions based on table size
                if num_players == 3:  # BTN, SB, BB only
                    self.logger.info("  3 players: BTN, SB, BB positions only")
                
                elif num_players == 4:  # Add UTG
                    utg_idx = (dealer_idx + 3) % num_players
                    active_players[utg_idx]['position'] = "UTG"
                    self.logger.info(f"  4 players: Adding UTG at seat {active_players[utg_idx].get('seat')}")
                
                elif num_players == 5:  # Add UTG and CO
                    utg_idx = (dealer_idx + 3) % num_players
                    co_idx = (dealer_idx + 4) % num_players
                    
                    active_players[utg_idx]['position'] = "UTG"
                    active_players[co_idx]['position'] = "CO"
                    
                    self.logger.info(f"  5 players: Adding UTG at seat {active_players[utg_idx].get('seat')}")
                    self.logger.info(f"  5 players: Adding CO at seat {active_players[co_idx].get('seat')}")
                
                elif num_players == 6:  # Add UTG, MP, CO
                    utg_idx = (dealer_idx + 3) % num_players
                    mp_idx = (dealer_idx + 4) % num_players
                    co_idx = (dealer_idx + 5) % num_players
                    
                    active_players[utg_idx]['position'] = "UTG"
                    active_players[mp_idx]['position'] = "MP"
                    active_players[co_idx]['position'] = "CO"
                    
                    self.logger.info(f"  6 players: Adding UTG at seat {active_players[utg_idx].get('seat')}")
                    self.logger.info(f"  6 players: Adding MP at seat {active_players[mp_idx].get('seat')}")
                    self.logger.info(f"  6 players: Adding CO at seat {active_players[co_idx].get('seat')}")
                
                elif num_players > 6:  # More complex positions for larger tables
                    self.logger.info(f"  {num_players} players: Assigning positions for larger table")
                    
                    # First assign UTG
                    utg_idx = (dealer_idx + 3) % num_players
                    active_players[utg_idx]['position'] = "UTG"
                    self.logger.info(f"  {num_players} players: Adding UTG at seat {active_players[utg_idx].get('seat')}")
                    
                    # Assign CO (cutoff) as the player right before the BTN
                    co_idx = (dealer_idx - 1 + num_players) % num_players
                    active_players[co_idx]['position'] = "CO"
                    self.logger.info(f"  {num_players} players: Adding CO at seat {active_players[co_idx].get('seat')}")
                    
                    # Assign middle positions
                    current_idx = (dealer_idx + 4) % num_players
                    position_count = 1
                    
                    while current_idx != co_idx:
                        if num_players >= 9 and position_count <= 2:
                            # For 9+ players, use UTG+1, UTG+2 for the first few positions
                            position_name = f"UTG+{position_count}"
                        else:
                            position_name = f"MP{position_count}"
                            
                        active_players[current_idx]['position'] = position_name
                        self.logger.info(f"  {num_players} players: Adding {position_name} at seat {active_players[current_idx].get('seat')}")
                        
                        position_count += 1
                        current_idx = (current_idx + 1) % num_players
                        
                        # Safety check to prevent infinite loops
                        if current_idx == dealer_idx:
                            self.logger.warning("Loop detected in position assignment. Breaking.")
                            break
            
            # Create a mapping from seat numbers to positions
            seat_to_position = {}
            for player in active_players:
                if 'position' in player and player.get('seat'):
                    seat_to_position[player['seat']] = player['position']
            
            # Update positions in the original player_data
            for player in self.player_data:
                if not player.get('is_empty') and player.get('seat') in seat_to_position:
                    player['position'] = seat_to_position[player['seat']]
            
            # Log final position assignments
            self.logger.info("Final position assignments:")
            for player in self.player_data:
                if player.get('is_my_player') and 'position' in player:
                    self.logger.info(f"MY PLAYER position: {player['position']} in seat {player['seat']}")
                elif 'position' in player:
                    self.logger.info(f"Player in seat {player.get('seat')}: {player.get('position')}")
        
        except ValueError:
            self.logger.error(f"Could not parse dealer_position: {self.table_data.get('dealer_position')} as int.")
        except Exception as e:
            self.logger.error(f"Unexpected error during internal position calculation: {e}", exc_info=True)

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
            self.logger.error("BeautifulSoup object (self.soup) not initialized before calling analyze_players.") # Replaced print with self.logger.error
            return []
        self.player_data = [] 
        active_player_already_identified_for_this_parse = False # New flag to track if an active player has been found

        # Find all elements that are marked as player areas
        player_area_elements = self.soup.find_all('div', class_='player-area')
        self.logger.info(f"Found {len(player_area_elements)} 'div.player-area' elements to process.")

        if not player_area_elements:
            self.logger.warning("No 'div.player-area' elements found. No players will be parsed.")
            return []
        
        for player_element in player_area_elements: # Iterate directly over all found player-area divs
            player_info = {
                'seat': None, 'name': 'N/A', 'stack': 'N/A', 'bet': '0', 
                'is_my_player': False, 'is_empty': False, 'cards': [], 
                'has_turn': False, # Initialize to False
                'has_hidden_cards': False
                # 'hand_rank' will be calculated by PokerBot using HandEvaluator
            }

            # Try to extract seat number from the player_element's classes
            element_classes = player_element.get('class', [])
            seat_match = None
            for c_name in element_classes:
                match = re.match(r'player-seat-(\d+)', c_name) # Regex to find player-seat-NUMBER
                if match:
                    seat_match = match
                    break
            
            if seat_match:
                player_info['seat'] = seat_match.group(1)
                player_info['id'] = player_info['seat'] 
            # else:
                # self.logger.debug(f"No 'player-seat-(\\d+)' class found directly on 'div.player-area' with classes {element_classes}. Seat will be None for now.")

            # Check if it's 'my-player'
            if 'my-player' in element_classes:
                player_info['is_my_player'] = True
            
            # Check for empty seat
            empty_seat_element = player_element.find('div', class_='empty-seat')
            if empty_seat_element and empty_seat_element.text.strip().lower() == 'empty':
                player_info['is_empty'] = True
                self.logger.debug(f"Identified as empty seat. Seat: {player_info['seat']}, Classes: {element_classes}")
                self.player_data.append(player_info) # Add empty seat to player data
                continue # Move to the next player_area_element

            # If it's not an empty seat, a seat number is crucial for further processing.
            # If we didn't find a seat number for this non-empty player, log and skip it.
            if not player_info['seat']:
                self.logger.warning(
                    f"Skipping 'div.player-area' element (classes: {element_classes}) "
                    f"as it's not marked empty and no 'player-seat-(\\d+)' class was found for it."
                )
                continue

            # From here, the original logic for a valid player_element continues
            # player_info has 'seat', 'id', and 'is_my_player' potentially set.
            # It's not an empty seat.

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
            
            # Determine if this player *would* be active based on local conditions
            current_player_meets_active_criteria = False
            
            # Check 1: 'player-active' class
            table_player_div = player_element.find('div', class_='table-player')
            if table_player_div and 'player-active' in table_player_div.get('class', []):
                current_player_meets_active_criteria = True
            
            if not current_player_meets_active_criteria:
                nameplate_div = player_element.find('div', class_='player-nameplate')
                if nameplate_div:
                    # Check 2: Visible 'text-countdown'
                    countdown_div = nameplate_div.find('div', class_='text-countdown')
                    if self._check_visibility_of_element_and_its_ancestors(countdown_div, nameplate_div):
                        current_player_meets_active_criteria = True
                    
                    if not current_player_meets_active_criteria: 
                        # Check 3: Visible 'timeout-wrapper'
                        timeout_wrapper_div = nameplate_div.find('div', class_='timeout-wrapper')
                        if self._check_visibility_of_element_and_its_ancestors(timeout_wrapper_div, nameplate_div):
                            current_player_meets_active_criteria = True
            
            # Now, decide if this player gets 'has_turn' based on the global flag
            if current_player_meets_active_criteria:
                if not active_player_already_identified_for_this_parse:
                    player_info['has_turn'] = True
                    active_player_already_identified_for_this_parse = True
                else:
                    # Another player was already marked as active. This one is not.
                    player_info['has_turn'] = False 
                    self.logger.warning(
                        f"Player {player_info.get('name', player_info.get('seat', 'UnknownSeat'))} "
                        f"(Classes: {player_element.get('class', [])}) "
                        f"met active criteria, but another player was already identified as active. "
                        f"HTML might be ambiguous or multiple turn indicators present."
                    )
            # player_info['has_turn'] remains False if current_player_meets_active_criteria is False

            if player_info['is_my_player']:
                player_info['available_actions'] = []
                player_info['is_all_in_call_available'] = False
                player_info['bet_to_call'] = 0 # Initialize

                actions_area_wrapper = self.soup.find('div', class_='table-actions-wrapper')
                actions_area = None
                if actions_area_wrapper:
                    actions_area = actions_area_wrapper.find('div', class_='actions-area')
                
                if not actions_area:
                    self.logger.warning("Could not find actions area ('div.actions-area' inside 'div.table-actions-wrapper'). No actions will be parsed.") # Replaced print with self.logger.warning
                else:
                    self.logger.info("Found actions area. Analyzing buttons...") # Replaced print with self.logger.info
                    # elements_to_check = actions_area.find_all(lambda tag: tag.name == 'div' and 'action-button' in tag.get('class', []))
                    # Find only direct children that are action buttons to avoid double counting
                    elements_to_check = actions_area.find_all('div', class_=re.compile(r'action-button'), recursive=False)
                    if not elements_to_check: # If no direct children, try a broader search but be wary of duplicates
                        elements_to_check = actions_area.find_all('div', class_=re.compile(r'action-button'))
                        # This broader search might re-introduce duplicates if the HTML is complex.
                        # A more robust solution would involve tracking processed elements or using more specific selectors.
                        # For now, we'll proceed and rely on the available_actions set to prevent functional duplicates.

                    self.logger.info(f"Found {len(elements_to_check)} potential action elements.") # Replaced print with self.logger.info
                    

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
                            self.logger.debug(f"Skipping element, no button text could be extracted: {el.name} {el_classes}") # Replaced print with self.logger.debug
                            continue

                        self.logger.debug(f"--- Debug Amount Parsing for element: ---") # Replaced print with self.logger.debug
                        self.logger.debug(f"Element raw text: '{el.text.strip()}'") # Replaced print with self.logger.debug
                        self.logger.debug(f"Processed button_text_content: '{button_text_content}'") # Replaced print with self.logger.debug

                        current_element_action_amount = 0.0
                        # Try to find amount in <span class="action-value">
                        amount_span = el.find('span', class_='action-value')
                        if amount_span and amount_span.text.strip():
                            amount_text = amount_span.text.strip()
                            self.logger.debug(f"Found amount span <span class='action-value'>: '{amount_text}'") # Replaced print with self.logger.debug
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
                                    self.logger.debug(f"Parsed amount from span: {current_element_action_amount}") # Replaced print with self.logger.debug
                                else:
                                    self.logger.debug(f"Amount text became empty after cleaning: '{amount_text}' -> '{text_to_parse}'") # Replaced print with self.logger.debug
                            except ValueError as e:
                                self.logger.warning(f"Could not parse amount from span text: '{amount_text}'. Cleaned: '{cleaned_amount_text}'. Error: {e}") # Replaced print with self.logger.warning
                        else:
                            # Fallback for table-action-button__amount (older structure or different HTML)
                            amount_el_fallback = el.find(class_='table-action-button__amount')
                            if amount_el_fallback and amount_el_fallback.text.strip():
                                amount_text_fallback = amount_el_fallback.text.strip()
                                self.logger.debug(f"Found fallback amount element <... class='table-action-button__amount'>: '{amount_text_fallback}'") # Replaced print with self.logger.debug
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
                                        self.logger.debug(f"Parsed amount from fallback: {current_element_action_amount}") # Replaced print with self.logger.debug
                                    else:
                                        self.logger.debug(f"Fallback amount text became empty after cleaning: '{amount_text_fallback}' -> '{text_to_parse_fallback}'") # Replaced print with self.logger.debug
                                except ValueError as e:
                                    self.logger.warning(f"Could not parse amount from fallback text: '{amount_text_fallback}'. Cleaned: '{cleaned_amount_text_fallback}'. Error: {e}") # Replaced print with self.logger.warning

                        # Update player_info['bet_to_call'] based on parsed amount and action type
                        if ('call' in button_text_content or 'all in' in button_text_content):
                            if current_element_action_amount > 0:
                                player_info['bet_to_call'] = current_element_action_amount
                                self.logger.debug(f"Updated player_info['bet_to_call'] to {player_info['bet_to_call']} from button '{button_text_content}' with amount {current_element_action_amount}") # Replaced print with self.logger.debug
                            elif 'call' in button_text_content and current_element_action_amount == 0:
                                if " 0" in button_text_content or " 0.00" in button_text_content : 
                                     player_info['bet_to_call'] = 0.0
                                     self.logger.debug(f"Button is 'Call 0', setting player_info['bet_to_call'] to 0.0") # Replaced print with self.logger.debug
                                else:
                                     self.logger.info(f"INFO: 'call' action found, but amount parsed from button is 0 (and not explicitly 'Call 0'). player_info['bet_to_call'] ({player_info.get('bet_to_call', 0)}) not updated by this button. This might require opponent's bet data.") # Replaced print with self.logger.info
                        
                        self.logger.debug(f"Player info bet_to_call after this element's logic: {player_info.get('bet_to_call', 0)}") # Replaced print with self.logger.debug
                        self.logger.debug(f"--- End Debug Amount Parsing ---") # Replaced print with self.logger.debug
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
                            self.logger.warning(f"Unrecognized action button text: '{button_text_content}'") # Replaced print with self.logger.warning
                        
                        if action_identified and action_identified not in unique_actions_found:
                            player_info['available_actions'].append(action_identified)
                            unique_actions_found.add(action_identified)
                        elif action_identified:
                            self.logger.debug(f"Action '{action_identified}' already processed for this player. Text: '{button_text_content}'") # Replaced print with self.logger.debug


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
                self.logger.debug(f"Final detected actions for player {player_info.get('name', 'N/A')}: {player_info['available_actions']}") # Replaced print with self.logger.debug
                self.logger.debug(f"Is all-in call available for player {player_info.get('name', 'N/A')}: {player_info['is_all_in_call_available']}") # Replaced print with self.logger.debug
                self.logger.debug(f"Player's bet_to_call: {player_info['bet_to_call']}") # Replaced print with self.logger.debug

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
                self.player_data.append(player_info)        # --- BEGIN POSITION CALCULATION ---
        if self.player_data and self.table_data.get('dealer_position'):
            try:
                # Always attempt to use the enhanced position calculator first
                if calculate_positions:
                    self.logger.info("Using enhanced position calculator from position_calculator module")
                    # Call the external position calculator with detailed logging
                    try:
                        self.player_data = calculate_positions(self.player_data, self.table_data['dealer_position'])
                        self.logger.info("Position calculation completed successfully with position_calculator")
                        
                        # Log the calculated positions
                        self.logger.info("Player positions after calculation:")
                        for player in self.player_data:
                            if not player.get('is_empty', False):
                                self.logger.info(f"  Seat: {player.get('seat', 'N/A')}, "
                                               f"Name: {player.get('name', 'N/A')}, "
                                               f"Position: {player.get('position', 'None')}, "
                                               f"Is my player: {player.get('is_my_player', False)}")
                                
                        # Additional logging for my player position
                        my_player = next((p for p in self.player_data if p.get('is_my_player')), None)
                        if my_player and 'position' in my_player:
                            self.logger.info(f"MY PLAYER position: {my_player['position']} in seat {my_player.get('seat')}")
                    
                    except Exception as calc_error:
                        self.logger.error(f"Error using external position calculator: {calc_error}")
                        self.logger.info("Falling back to internal position calculation")
                        # Fall back to internal calculation
                        self._calculate_positions_internal()
                else:
                    # Fall back to the internal calculation if position_calculator not available
                    self.logger.info("Enhanced position calculator not available, using internal calculation")
                    self._calculate_positions_internal()
                    
            except Exception as e:
                self.logger.error(f"Fatal error during position calculation: {e}", exc_info=True)
                self.logger.error("Position calculation failed - positions may be incorrect")
        # --- END POSITION CALCULATION ---
        return self.player_data
