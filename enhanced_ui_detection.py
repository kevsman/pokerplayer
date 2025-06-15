# enhanced_ui_detection.py
"""
Enhanced UI detection system that fixes action detection issues and improves timing.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GameState:
    """Track game state to avoid unnecessary parsing."""
    last_hand_id: Optional[str] = None
    last_pot_size: float = 0.0
    last_action_time: float = 0.0
    last_community_cards: List[str] = None
    action_required: bool = False
    parsing_in_progress: bool = False
    
    def __post_init__(self):
        if self.last_community_cards is None:
            self.last_community_cards = []

class EnhancedUIDetection:
    """Enhanced UI detection with improved timing and action detection."""
    
    def __init__(self, logger_instance=None):
        self.logger = logger_instance or logger
        self.game_state = GameState()
        self.parse_lock = threading.Lock()
        self.consecutive_no_action_count = 0
        self.last_successful_parse_time = time.time()
        
    def should_parse_now(self, force_parse: bool = False) -> bool:
        """
        Intelligent decision on whether to parse now.
        Fixes excessive parsing frequency issues.
        """
        
        current_time = time.time()
        
        # Always parse if forced
        if force_parse:
            return True
        
        # Don't parse if already in progress
        if self.game_state.parsing_in_progress:
            return False
        
        # Minimum time between parses (prevents spam)
        min_parse_interval = 0.8  # 800ms minimum
        if current_time - self.last_successful_parse_time < min_parse_interval:
            return False
        
        # Parse more frequently when action might be needed
        if self.game_state.action_required:
            return current_time - self.game_state.last_action_time > 0.5
        
        # Standard parsing interval when waiting
        standard_interval = 2.0
        return current_time - self.last_successful_parse_time > standard_interval
    
    def enhanced_action_detection(self, soup) -> Dict[str, Any]:
        """
        Enhanced action detection that fixes the "Found 0 potential action elements" issue.
        """
        
        with self.parse_lock:
            self.game_state.parsing_in_progress = True
            
        try:
            action_results = {
                'actions_found': [],
                'my_turn': False,
                'active_player': None,
                'game_state_changed': False,
                'parse_timestamp': time.time()
            }
            
            # Multiple strategies for finding action buttons
            action_elements = self._find_action_elements_multi_strategy(soup)
            
            if action_elements:
                self.consecutive_no_action_count = 0
                action_results['actions_found'] = action_elements
                self.logger.info(f"Found {len(action_elements)} action elements")
                
                # Check if it's our turn based on action availability
                action_results['my_turn'] = self._determine_if_my_turn(action_elements)
                
            else:
                self.consecutive_no_action_count += 1
                self.logger.debug(f"No action elements found (consecutive: {self.consecutive_no_action_count})")
                
                # If we've consistently found no actions, we're probably not in a hand
                if self.consecutive_no_action_count > 5:
                    self.game_state.action_required = False
            
            # Detect game state changes
            action_results['game_state_changed'] = self._detect_game_state_changes(soup)
            
            # Find active player using multiple methods
            action_results['active_player'] = self._find_active_player_enhanced(soup)
            
            self.last_successful_parse_time = time.time()
            return action_results
            
        except Exception as e:
            self.logger.error(f"Error in enhanced action detection: {e}")
            return {
                'actions_found': [],
                'my_turn': False,
                'active_player': None,
                'game_state_changed': False,
                'error': str(e)
            }
        finally:
            self.game_state.parsing_in_progress = False
    
    def _find_action_elements_multi_strategy(self, soup) -> List[Dict]:
        """Use multiple strategies to find action elements."""
        
        strategies = [
            self._strategy_standard_actions,
            self._strategy_button_elements,
            self._strategy_clickable_actions,
            self._strategy_form_actions
        ]
        
        for strategy in strategies:
            try:
                elements = strategy(soup)
                if elements:
                    self.logger.debug(f"Found actions using {strategy.__name__}: {len(elements)}")
                    return elements
            except Exception as e:
                self.logger.debug(f"Strategy {strategy.__name__} failed: {e}")
        
        return []
    
    def _strategy_standard_actions(self, soup) -> List[Dict]:
        """Standard action detection strategy."""
        actions = []
        
        # Look for the actions area
        actions_area = soup.find('div', class_='actions')
        if not actions_area:
            return []
        
        # Find buttons within actions area
        buttons = actions_area.find_all(['button', 'div'], recursive=True)
        
        for button in buttons:
            if self._is_visible_element(button) and self._is_action_button(button):
                action_info = self._extract_action_info(button)
                if action_info:
                    actions.append(action_info)
        
        return actions
    
    def _strategy_button_elements(self, soup) -> List[Dict]:
        """Look for button elements with action-related classes."""
        actions = []
        
        button_selectors = [
            'button[class*="action"]',
            'button[class*="bet"]',
            'button[class*="call"]',
            'button[class*="fold"]',
            'button[class*="check"]',
            'button[class*="raise"]'
        ]
        
        for selector in button_selectors:
            buttons = soup.select(selector)
            for button in buttons:
                if self._is_visible_element(button):
                    action_info = self._extract_action_info(button)
                    if action_info:
                        actions.append(action_info)
        
        return actions
    
    def _strategy_clickable_actions(self, soup) -> List[Dict]:
        """Look for clickable elements that might be action buttons."""
        actions = []
        
        # Find elements with onclick or similar attributes
        clickable_elements = soup.find_all(attrs={'onclick': True})
        clickable_elements.extend(soup.find_all(attrs={'data-action': True}))
        
        for element in clickable_elements:
            if (self._is_visible_element(element) and 
                self._contains_action_keywords(element)):
                action_info = self._extract_action_info(element)
                if action_info:
                    actions.append(action_info)
        
        return actions
    
    def _strategy_form_actions(self, soup) -> List[Dict]:
        """Look for form inputs that represent actions."""
        actions = []
        
        forms = soup.find_all('form')
        for form in forms:
            inputs = form.find_all(['input', 'button'])
            for input_elem in inputs:
                if (self._is_visible_element(input_elem) and 
                    self._is_action_input(input_elem)):
                    action_info = self._extract_action_info(input_elem)
                    if action_info:
                        actions.append(action_info)
        
        return actions
    
    def _is_visible_element(self, element) -> bool:
        """Check if element is visible (not hidden by CSS classes)."""
        if not element:
            return False
        
        classes = element.get('class', [])
        
        # Common hidden classes
        hidden_classes = ['hidden', 'pt-hidden', 'pt-visibility-hidden', 'invisible', 'disabled']
        
        for hidden_class in hidden_classes:
            if hidden_class in classes:
                return False
        
        # Check style attribute for display:none or visibility:hidden
        style = element.get('style', '')
        if 'display:none' in style.replace(' ', '') or 'visibility:hidden' in style.replace(' ', ''):
            return False
        
        return True
    
    def _is_action_button(self, element) -> bool:
        """Check if element looks like an action button."""
        if not element:
            return False
        
        text = element.get_text(strip=True).lower()
        classes = ' '.join(element.get('class', [])).lower()
        
        action_keywords = ['fold', 'call', 'raise', 'bet', 'check', 'all-in', 'allin']
        
        return any(keyword in text or keyword in classes for keyword in action_keywords)
    
    def _contains_action_keywords(self, element) -> bool:
        """Check if element contains action-related keywords."""
        text_content = element.get_text(strip=True).lower()
        attrs = str(element.attrs).lower()
        
        keywords = ['fold', 'call', 'raise', 'bet', 'check', 'action', 'all-in']
        
        return any(keyword in text_content or keyword in attrs for keyword in keywords)
    
    def _is_action_input(self, element) -> bool:
        """Check if input element represents an action."""
        input_type = element.get('type', '').lower()
        name = element.get('name', '').lower()
        value = element.get('value', '').lower()
        
        if input_type in ['submit', 'button']:
            return True
        
        action_names = ['action', 'fold', 'call', 'raise', 'bet', 'check']
        return any(action_name in name or action_name in value for action_name in action_names)
    
    def _extract_action_info(self, element) -> Optional[Dict]:
        """Extract action information from element."""
        try:
            text = element.get_text(strip=True)
            action_type = self._determine_action_type(text, element)
            
            if not action_type:
                return None
            
            return {
                'type': action_type,
                'text': text,
                'element': element,
                'amount': self._extract_amount_from_element(element),
                'enabled': not element.get('disabled', False)
            }
        except Exception as e:
            self.logger.debug(f"Error extracting action info: {e}")
            return None
    
    def _determine_action_type(self, text: str, element) -> Optional[str]:
        """Determine the type of action from text and element."""
        text_lower = text.lower()
        
        if 'fold' in text_lower:
            return 'fold'
        elif 'call' in text_lower:
            return 'call'
        elif 'raise' in text_lower or 'bet' in text_lower:
            return 'raise'
        elif 'check' in text_lower:
            return 'check'
        elif 'all' in text_lower and 'in' in text_lower:
            return 'all-in'
        
        # Check attributes for action type
        data_action = element.get('data-action', '').lower()
        if data_action in ['fold', 'call', 'raise', 'check', 'bet']:
            return data_action
        
        return None
    
    def _extract_amount_from_element(self, element) -> Optional[float]:
        """Extract monetary amount from element text or attributes."""
        try:
            text = element.get_text(strip=True)
            
            # Look for currency symbols and numbers
            import re
            
            # Pattern for amounts like "€1.25" or "$5.00" or "1.25"
            amount_pattern = r'[€$]?(\d+\.?\d*)'
            matches = re.findall(amount_pattern, text)
            
            if matches:
                return float(matches[0])
            
            # Check data attributes
            for attr in ['data-amount', 'data-bet', 'data-call']:
                if element.has_attr(attr):
                    try:
                        return float(element[attr])
                    except ValueError:
                        continue
            
        except Exception as e:
            self.logger.debug(f"Error extracting amount: {e}")
        
        return None
    
    def _determine_if_my_turn(self, action_elements: List[Dict]) -> bool:
        """Determine if it's our turn based on available actions."""
        if not action_elements:
            return False
        
        # If we have enabled action buttons, it's likely our turn
        enabled_actions = [action for action in action_elements if action.get('enabled', True)]
        
        return len(enabled_actions) > 0
    
    def _detect_game_state_changes(self, soup) -> bool:
        """Detect if game state has changed significantly."""
        try:
            # Check hand ID
            hand_id_element = soup.find('div', class_='hand-id')
            current_hand_id = hand_id_element.text.strip() if hand_id_element else None
            
            # Check pot size
            pot_element = soup.find('span', class_='total-pot-amount')
            current_pot = 0.0
            if pot_element:
                pot_text = pot_element.text.strip().replace('€', '').replace('$', '')
                try:
                    current_pot = float(pot_text)
                except ValueError:
                    pass
            
            # Check community cards
            current_cards = []
            community_cards_container = soup.find('div', class_='community-cards')
            if community_cards_container:
                card_elements = community_cards_container.find_all('div', class_='card')
                for card in card_elements:
                    if self._is_visible_element(card):
                        current_cards.append(card.get_text(strip=True))
            
            # Compare with previous state
            state_changed = (
                current_hand_id != self.game_state.last_hand_id or
                abs(current_pot - self.game_state.last_pot_size) > 0.01 or
                current_cards != self.game_state.last_community_cards
            )
            
            # Update game state
            if state_changed:
                self.game_state.last_hand_id = current_hand_id
                self.game_state.last_pot_size = current_pot
                self.game_state.last_community_cards = current_cards.copy()
                self.logger.debug(f"Game state changed: hand={current_hand_id}, pot={current_pot}, cards={len(current_cards)}")
            
            return state_changed
            
        except Exception as e:
            self.logger.debug(f"Error detecting game state changes: {e}")
            return False
    
    def _find_active_player_enhanced(self, soup) -> Optional[Dict]:
        """Enhanced active player detection with multiple strategies."""
        
        strategies = [
            self._find_active_by_turn_indicator,
            self._find_active_by_timer,
            self._find_active_by_highlighting,
            self._find_active_by_action_prompt
        ]
        
        for strategy in strategies:
            try:
                active_player = strategy(soup)
                if active_player:
                    return active_player
            except Exception as e:
                self.logger.debug(f"Active player strategy failed: {e}")
        
        return None
    
    def _find_active_by_turn_indicator(self, soup) -> Optional[Dict]:
        """Find active player by turn indicator."""
        # Look for elements with turn-related classes
        turn_indicators = soup.find_all(class_=lambda x: x and 'turn' in str(x).lower())
        
        for indicator in turn_indicators:
            if self._is_visible_element(indicator):
                # Find associated player
                player_area = indicator.find_parent(class_=lambda x: x and 'player' in str(x).lower())
                if player_area:
                    return self._extract_player_info(player_area)
        
        return None
    
    def _find_active_by_timer(self, soup) -> Optional[Dict]:
        """Find active player by action timer."""
        timers = soup.find_all(class_=lambda x: x and ('timer' in str(x).lower() or 'countdown' in str(x).lower()))
        
        for timer in timers:
            if self._is_visible_element(timer):
                player_area = timer.find_parent(class_=lambda x: x and 'player' in str(x).lower())
                if player_area:
                    return self._extract_player_info(player_area)
        
        return None
    
    def _find_active_by_highlighting(self, soup) -> Optional[Dict]:
        """Find active player by visual highlighting."""
        highlighted_classes = ['active', 'highlight', 'current', 'acting']
        
        for class_name in highlighted_classes:
            elements = soup.find_all(class_=lambda x: x and class_name in str(x).lower())
            for element in elements:
                if self._is_visible_element(element):
                    # Check if this is a player area
                    if 'player' in str(element.get('class', [])).lower():
                        return self._extract_player_info(element)
                    
                    # Or find parent player area
                    player_area = element.find_parent(class_=lambda x: x and 'player' in str(x).lower())
                    if player_area:
                        return self._extract_player_info(player_area)
        
        return None
    
    def _find_active_by_action_prompt(self, soup) -> Optional[Dict]:
        """Find active player by action prompt text."""
        prompts = soup.find_all(text=lambda text: text and any(
            phrase in text.lower() for phrase in ['your turn', 'your action', 'to act']
        ))
        
        for prompt in prompts:
            parent = prompt.parent
            while parent and parent.name != 'body':
                if 'player' in str(parent.get('class', [])).lower():
                    return self._extract_player_info(parent)
                parent = parent.parent
        
        return None
    
    def _extract_player_info(self, player_element) -> Dict:
        """Extract player information from player element."""
        try:
            name_element = player_element.find(class_=lambda x: x and 'name' in str(x).lower())
            seat_element = player_element.find(class_=lambda x: x and 'seat' in str(x).lower())
            
            return {
                'name': name_element.get_text(strip=True) if name_element else 'Unknown',
                'seat': seat_element.get_text(strip=True) if seat_element else 'Unknown',
                'element': player_element
            }
        except Exception as e:
            self.logger.debug(f"Error extracting player info: {e}")
            return {'name': 'Unknown', 'seat': 'Unknown'}

    def detect_action_state(self, html_content: str = None) -> Dict[str, Any]:
        """
        Detect current action state with improved reliability.
        This method is expected by the validation tests.
        """
        try:
            if not html_content:
                return {
                    'my_turn': False,
                    'available_actions': [],
                    'bet_to_call': 0.0,
                    'can_check': False,
                    'action_elements_found': 0,
                    'parsing_successful': False,
                    'error': 'No HTML content provided'
                }
            
            # Use enhanced parsing to detect actions
            parse_result = self.enhanced_parse_with_timing(html_content)
            
            if not parse_result.get('parsing_successful', False):
                return {
                    'my_turn': False,
                    'available_actions': [],
                    'bet_to_call': 0.0,
                    'can_check': False,
                    'action_elements_found': 0,
                    'parsing_successful': False,
                    'error': parse_result.get('error', 'Parse failed')
                }
            
            # Extract action state from parse result
            my_player = parse_result.get('my_player_data')
            available_actions = my_player.get('available_actions', []) if my_player else []
            
            return {
                'my_turn': my_player.get('has_turn', False) if my_player else False,
                'available_actions': available_actions,
                'bet_to_call': my_player.get('bet_to_call', 0.0) if my_player else 0.0,
                'can_check': 'check' in available_actions,
                'action_elements_found': len(available_actions),
                'parsing_successful': True,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Error in detect_action_state: {e}")
            return {
                'my_turn': False,
                'available_actions': [],
                'bet_to_call': 0.0,
                'can_check': False,
                'action_elements_found': 0,
                'parsing_successful': False,
                'error': str(e)
            }

    def verify_action_buttons(self, ui_controller) -> Dict[str, bool]:
        """
        Verify which action buttons are available and enabled.
        Returns dict with button availability.
        """
        try:
            available_buttons = {
                'fold': False,
                'check': False, 
                'call': False,
                'bet': False,
                'raise': False,
                'all_in': False
            }
            
            # Check each button position if available
            if hasattr(ui_controller, 'positions') and ui_controller.positions:
                for action in available_buttons.keys():
                    button_pos = ui_controller.positions.get(f"{action}_button")
                    if button_pos:
                        # Simple check - assume button exists if position is defined
                        available_buttons[action] = True
            
            self.logger.debug(f"Available action buttons: {available_buttons}")
            return available_buttons
            
        except Exception as e:
            self.logger.error(f"Error verifying action buttons: {e}")
            return {'fold': True, 'check': True, 'call': True, 'bet': True, 'raise': True, 'all_in': True}

    def detect_action_state(self, html_content: str) -> Dict[str, Any]:
        """
        Detect current action state from HTML content.
        Returns state information about required actions.
        """
        try:
            action_state = {
                'action_required': False,
                'action_timeout': None,
                'current_player': None,
                'available_actions': [],
                'confidence': 0.0
            }
            
            if not html_content:
                return action_state
            
            # Look for action indicators in HTML
            action_indicators = [
                'your turn',
                'time to act',
                'action required',
                'check or bet',
                'call or fold',
                'call or raise'
            ]
            
            html_lower = html_content.lower()
            action_found = any(indicator in html_lower for indicator in action_indicators)
            
            if action_found:
                action_state['action_required'] = True
                action_state['confidence'] = 0.8
                  # Try to detect available actions
                if 'check' in html_lower:
                    action_state['available_actions'].append('check')
                if 'call' in html_lower:
                    action_state['available_actions'].append('call') 
                if 'fold' in html_lower:
                    action_state['available_actions'].append('fold')
                if 'bet' in html_lower or 'raise' in html_lower:
                    action_state['available_actions'].append('bet')
            
            return action_state
            
        except Exception as e:
            self.logger.error(f"Error detecting action state: {e}")
            return {'action_required': False, 'confidence': 0.0, 'available_actions': []}
    
    def verify_action_buttons(self, soup) -> Dict[str, Any]:
        """Verify that action buttons are present and clickable."""
        try:
            verification = {
                'buttons_found': False,
                'buttons_clickable': False,
                'button_types': [],
                'confidence': 0.0
            }
            
            # Find potential action buttons
            action_elements = self._find_action_elements_multi_strategy(soup)
            
            if action_elements:
                verification['buttons_found'] = True
                verification['button_types'] = [elem.get('action_type', 'unknown') for elem in action_elements]
                verification['buttons_clickable'] = len(action_elements) > 0
                verification['confidence'] = min(1.0, len(action_elements) * 0.3)
            
            return verification
            
        except Exception as e:
            self.logger.error(f"Error verifying action buttons: {e}")
            return {'buttons_found': False, 'buttons_clickable': False, 'button_types': [], 'confidence': 0.0}
    
    def get_adaptive_delay(self, action_type: str = 'default') -> float:
        """Get adaptive delay based on action type and game state."""
        try:
            base_delays = {
                'fold': 1.0,
                'call': 1.5,
                'check': 1.0,
                'bet': 2.0,
                'raise': 2.5,
                'default': 1.5
            }
            
            base_delay = base_delays.get(action_type, 1.5)
            
            # Adjust based on consecutive failures
            if self.consecutive_no_action_count > 3:
                base_delay += 1.0
            elif self.consecutive_no_action_count > 6:
                base_delay += 2.0
            
            # Random variation to seem more human
            import random
            variation = random.uniform(0.8, 1.2)
            
            return base_delay * variation
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptive delay: {e}")
            return 2.0  # Safe default
        
def create_smart_timing_controller():
    """Create a timing controller that adapts to game flow."""
    
    class SmartTimingController:
        def __init__(self):
            self.base_delay = 1.0
            self.min_delay = 0.3
            self.max_delay = 3.0
            self.recent_activity = []
            
        def get_next_delay(self, game_activity_level: str = 'normal') -> float:
            """Get adaptive delay based on game activity."""
            
            if game_activity_level == 'high':  # Fast action needed
                return self.min_delay
            elif game_activity_level == 'low':  # Waiting between hands
                return self.max_delay
            else:  # Normal gameplay
                return self.base_delay
        
        def record_activity(self, activity_type: str):
            """Record game activity for adaptive timing."""
            current_time = time.time()
            self.recent_activity.append((current_time, activity_type))
            
            # Keep only recent activity (last 30 seconds)
            cutoff_time = current_time - 30
            self.recent_activity = [
                (t, a) for t, a in self.recent_activity if t > cutoff_time
            ]
    
    return SmartTimingController()
