# enhanced_action_detection.py
"""
Enhanced action detection with multiple fallback strategies and confidence scoring.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class ActionElement:
    """Represents a detected action element."""
    action_type: str
    element_id: str
    confidence: float
    selector: str
    text_content: str
    is_enabled: bool

class EnhancedActionDetector:
    """Enhanced action detection with multiple strategies."""
    
    def __init__(self, parser_instance):
        self.parser = parser_instance
        self.logger = logging.getLogger(__name__)
        
        # Multiple selector strategies
        self.action_selectors = {
            'primary': [
                'button[data-action="fold"]',
                'button[data-action="check"]', 
                'button[data-action="call"]',
                'button[data-action="raise"]',
                'button[data-action="all-in"]'
            ],
            'secondary': [
                '.action-button',
                '.poker-action',
                'button.fold-btn',
                'button.check-btn',
                'button.call-btn', 
                'button.raise-btn',
                'button.allin-btn'
            ],
            'text_based': [
                'button:contains("Fold")',
                'button:contains("Check")',
                'button:contains("Call")',
                'button:contains("Raise")',
                'button:contains("All")'
            ],
            'generic': [
                'button:visible',
                'input[type="button"]:visible',
                '.clickable:visible'
            ]
        }
        
        # Action keywords for text analysis
        self.action_keywords = {
            'fold': ['fold', 'forfeit', 'give up'],
            'check': ['check', 'pass'],
            'call': ['call', 'match'],
            'raise': ['raise', 'bet', 'increase'],
            'all_in': ['all in', 'all-in', 'allin', 'shove']
        }
        
    def detect_available_actions(self, soup=None) -> Tuple[List[ActionElement], float]:
        """
        Detect available actions with confidence scoring.
        Returns (actions, overall_confidence)
        """
        if not soup:
            soup = self.parser.soup
            
        if not soup:
            return [], 0.0
            
        all_actions = []
        strategy_results = {}
        
        # Try multiple detection strategies
        for strategy_name, selectors in self.action_selectors.items():
            actions = self._detect_with_strategy(soup, strategy_name, selectors)
            strategy_results[strategy_name] = actions
            all_actions.extend(actions)
            
        # Consolidate and score results
        consolidated_actions = self._consolidate_actions(all_actions)
        overall_confidence = self._calculate_overall_confidence(strategy_results)
        
        self.logger.debug(f"Detected {len(consolidated_actions)} actions with confidence {overall_confidence:.2f}")
        
        return consolidated_actions, overall_confidence
        
    def _detect_with_strategy(self, soup, strategy_name: str, selectors: List[str]) -> List[ActionElement]:
        """Detect actions using a specific strategy."""
        actions = []
        
        try:
            if strategy_name == 'text_based':
                actions = self._detect_by_text_content(soup)
            else:
                for selector in selectors:
                    elements = soup.select(selector) if hasattr(soup, 'select') else []
                    for element in elements:
                        action = self._analyze_element(element, selector, strategy_name)
                        if action:
                            actions.append(action)
                            
        except Exception as e:
            self.logger.debug(f"Error in strategy {strategy_name}: {e}")
            
        return actions
        
    def _detect_by_text_content(self, soup) -> List[ActionElement]:
        """Detect actions by analyzing text content."""
        actions = []
        
        try:
            # Find all clickable elements
            clickable_elements = soup.find_all(['button', 'input', 'a', 'div'], 
                                             attrs={'onclick': True}) or []
            clickable_elements.extend(soup.find_all(['button', 'input']) or [])
            
            for element in clickable_elements:
                text = self._get_element_text(element).lower()
                action_type = self._classify_text_action(text)
                
                if action_type:
                    confidence = self._calculate_text_confidence(text, action_type)
                    action = ActionElement(
                        action_type=action_type,
                        element_id=element.get('id', ''),
                        confidence=confidence,
                        selector=f"text_match:{text[:20]}",
                        text_content=text,
                        is_enabled=not element.get('disabled', False)
                    )
                    actions.append(action)
                    
        except Exception as e:
            self.logger.debug(f"Error in text-based detection: {e}")
            
        return actions
        
    def _analyze_element(self, element, selector: str, strategy: str) -> Optional[ActionElement]:
        """Analyze a single element for action potential."""
        try:
            # Get element properties
            element_id = element.get('id', '')
            classes = element.get('class', [])
            text = self._get_element_text(element).lower()
            data_action = element.get('data-action', '')
            
            # Determine action type
            action_type = None
            if data_action:
                action_type = data_action.lower()
            else:
                action_type = self._classify_text_action(text)
                if not action_type:
                    action_type = self._classify_by_classes(classes)
                    
            if not action_type:
                return None
                
            # Calculate confidence
            confidence = self._calculate_element_confidence(element, action_type, strategy)
            
            return ActionElement(
                action_type=action_type,
                element_id=element_id,
                confidence=confidence,
                selector=selector,
                text_content=text,
                is_enabled=not element.get('disabled', False)
            )
            
        except Exception as e:
            self.logger.debug(f"Error analyzing element: {e}")
            return None
            
    def _get_element_text(self, element) -> str:
        """Get text content from element."""
        try:
            if hasattr(element, 'get_text'):
                return element.get_text(strip=True)
            elif hasattr(element, 'text'):
                return element.text.strip()
            else:
                return str(element).strip()
        except:
            return ""
            
    def _classify_text_action(self, text: str) -> Optional[str]:
        """Classify action based on text content."""
        text = text.lower().strip()
        
        for action_type, keywords in self.action_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return action_type
                    
        return None
        
    def _classify_by_classes(self, classes: List[str]) -> Optional[str]:
        """Classify action based on CSS classes."""
        class_str = ' '.join(classes).lower()
        
        if any(word in class_str for word in ['fold', 'forfeit']):
            return 'fold'
        elif any(word in class_str for word in ['check', 'pass']):
            return 'check'
        elif any(word in class_str for word in ['call', 'match']):
            return 'call'
        elif any(word in class_str for word in ['raise', 'bet']):
            return 'raise'
        elif any(word in class_str for word in ['allin', 'all-in', 'shove']):
            return 'all_in'
            
        return None
        
    def _calculate_element_confidence(self, element, action_type: str, strategy: str) -> float:
        """Calculate confidence score for an element."""
        confidence = 0.5  # Base confidence
        
        # Strategy-based adjustments
        strategy_weights = {
            'primary': 1.0,
            'secondary': 0.8,
            'text_based': 0.6,
            'generic': 0.3
        }
        confidence *= strategy_weights.get(strategy, 0.5)
        
        # Element properties
        if element.get('data-action'):
            confidence += 0.3
        if element.get('id'):
            confidence += 0.1
        if not element.get('disabled', False):
            confidence += 0.2
        else:
            confidence -= 0.3
            
        # Text content quality
        text = self._get_element_text(element).lower()
        if action_type in text:
            confidence += 0.2
            
        return min(1.0, max(0.0, confidence))
        
    def _calculate_text_confidence(self, text: str, action_type: str) -> float:
        """Calculate confidence for text-based detection."""
        confidence = 0.4  # Base for text detection
        
        # Exact keyword match
        keywords = self.action_keywords.get(action_type, [])
        for keyword in keywords:
            if keyword == text.strip():
                confidence += 0.4
            elif keyword in text:
                confidence += 0.2
                
        return min(1.0, confidence)
        
    def _consolidate_actions(self, actions: List[ActionElement]) -> List[ActionElement]:
        """Consolidate duplicate actions and pick best candidates."""
        if not actions:
            return []
            
        # Group by action type
        action_groups = {}
        for action in actions:
            if action.action_type not in action_groups:
                action_groups[action.action_type] = []
            action_groups[action.action_type].append(action)
            
        # Pick best candidate for each action type
        consolidated = []
        for action_type, candidates in action_groups.items():
            # Sort by confidence and enabled status
            candidates.sort(key=lambda x: (x.is_enabled, x.confidence), reverse=True)
            best_candidate = candidates[0]
            
            # Only include if confidence is reasonable
            if best_candidate.confidence > 0.3:
                consolidated.append(best_candidate)
                
        return consolidated
        
    def _calculate_overall_confidence(self, strategy_results: Dict) -> float:
        """Calculate overall confidence in action detection."""
        if not strategy_results:
            return 0.0
            
        # Weight strategies by reliability
        total_weight = 0.0
        weighted_score = 0.0
        
        strategy_weights = {
            'primary': 1.0,
            'secondary': 0.7,
            'text_based': 0.5,
            'generic': 0.2
        }
        
        for strategy, actions in strategy_results.items():
            weight = strategy_weights.get(strategy, 0.3)
            if actions:
                avg_confidence = sum(a.confidence for a in actions) / len(actions)
                weighted_score += weight * avg_confidence
                total_weight += weight
            else:
                # Penalty for strategies that found nothing
                total_weight += weight * 0.1
                
        return weighted_score / total_weight if total_weight > 0 else 0.0
        
    def verify_action_availability(self, action_type: str) -> bool:
        """Verify that a specific action is actually available."""
        actions, confidence = self.detect_available_actions()
        
        for action in actions:
            if action.action_type == action_type and action.is_enabled:
                return True
                
        return False
        
    def get_action_confidence(self, action_type: str) -> float:
        """Get confidence score for a specific action type."""
        actions, _ = self.detect_available_actions()
        
        for action in actions:
            if action.action_type == action_type:
                return action.confidence
                
        return 0.0

def create_enhanced_action_detector(parser_instance):
    """Factory function to create enhanced action detector."""
    return EnhancedActionDetector(parser_instance)
