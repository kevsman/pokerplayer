"""
Hand History Tracker for Poker Bot
Tracks and maintains the history of actions for each hand across all streets
(preflop, flop, turn, river).
"""

import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

class HandAction:
    """Represents a single poker action in a hand"""
    
    def __init__(self, player_name: str, action_type: str, amount: float, street: str, position: str):
        """
        Initialize a hand action.
        
        Args:
            player_name: Name of the player who took the action
            action_type: Type of action (fold, check, call, raise, bet)
            amount: Bet amount (0 for check/fold)
            street: The street on which the action occurred (preflop, flop, turn, river)
            position: Player's position (BTN, SB, BB, etc.)
        """
        self.player_name = player_name
        self.action_type = action_type
        self.amount = amount
        self.street = street
        self.position = position
    
    def __str__(self):
        if self.action_type in ['check', 'fold']:
            return f"{self.player_name} ({self.position}): {self.action_type}"
        return f"{self.player_name} ({self.position}): {self.action_type} {self.amount:.2f}"


class HandHistory:
    """Tracks the history of actions in a poker hand"""
    
    def __init__(self, hand_id: str = "Unknown"):
        """
        Initialize a new hand history.
        
        Args:
            hand_id: Unique identifier for the hand
        """
        self.hand_id = hand_id
        self.actions_by_street = {
            "preflop": [],
            "flop": [],
            "turn": [],
            "river": []
        }
        self.pot_size_by_street = {
            "preflop": 0.0,
            "flop": 0.0,
            "turn": 0.0,
            "river": 0.0
        }
        self.aggressor_by_street = {
            "preflop": None,
            "flop": None,
            "turn": None,
            "river": None
        }
        self.raises_by_street = {
            "preflop": 0,
            "flop": 0, 
            "turn": 0,
            "river": 0
        }
        self.community_cards = {
            "flop": [],
            "turn": [],
            "river": []
        }
        self.player_cards = {}  # Map player name to their hole cards
        self.current_street = "preflop"
        self.is_completed = False
        
        # Player-specific tracked information
        self.player_actions_by_street = defaultdict(lambda: {
            "preflop": [],
            "flop": [],
            "turn": [],
            "river": []
        })

    def add_action(self, player_name: str, action_type: str, amount: float, 
                  street: str, position: str) -> None:
        """
        Add a player action to the hand history.
        
        Args:
            player_name: Name of the player who took the action
            action_type: Type of action (fold, check, call, raise, bet)
            amount: Bet amount (0 for check/fold)
            street: The street on which the action occurred
            position: Player's position
        """
        if self.is_completed:
            logger.warning(f"Attempting to add action to completed hand {self.hand_id}")
            return
        
        if street not in self.actions_by_street:
            logger.error(f"Invalid street: {street}")
            return
            
        action = HandAction(player_name, action_type, amount, street, position)
        self.actions_by_street[street].append(action)
        self.player_actions_by_street[player_name][street].append(action)
        
        # Update aggressor if this is a bet or raise
        if action_type in ['bet', 'raise']:
            self.aggressor_by_street[street] = player_name
            self.raises_by_street[street] += 1
        
        # Update current street if needed
        street_order = ["preflop", "flop", "turn", "river"]
        if street_order.index(street) > street_order.index(self.current_street):
            self.current_street = street

    def add_community_cards(self, street: str, cards: List[str]) -> None:
        """
        Add community cards for a specific street.
        
        Args:
            street: The street (flop, turn, river)
            cards: List of cards in string format (e.g., ['Ah', 'Kd', 'Qc'])
        """
        if street in self.community_cards:
            self.community_cards[street] = cards
    
    def add_player_cards(self, player_name: str, cards: List[str]) -> None:
        """
        Add hole cards for a specific player.
        
        Args:
            player_name: Player's name
            cards: List of hole cards (e.g., ['Ah', 'Kd'])
        """
        self.player_cards[player_name] = cards
    
    def update_pot_size(self, street: str, pot_size: float) -> None:
        """
        Update the pot size for a specific street.
        
        Args:
            street: The street (preflop, flop, turn, river)
            pot_size: Current pot size
        """
        if street in self.pot_size_by_street:
            self.pot_size_by_street[street] = pot_size
    
    def complete_hand(self) -> None:
        """Mark the hand as completed."""
        self.is_completed = True
    
    def get_player_action_types(self, player_name: str, street: str) -> List[str]:
        """
        Get all action types for a specific player on a specific street.
        
        Args:
            player_name: Player's name
            street: The street (preflop, flop, turn, river)
            
        Returns:
            List of action types (e.g., ['call', 'raise'])
        """
        if street not in self.actions_by_street:
            return []
            
        return [action.action_type 
                for action in self.actions_by_street[street] 
                if action.player_name == player_name]
    
    def is_player_aggressor(self, player_name: str, street: str) -> bool:
        """
        Check if player was the aggressor on a specific street.
        
        Args:
            player_name: Player's name
            street: The street to check
            
        Returns:
            True if player was the aggressor, False otherwise
        """
        return self.aggressor_by_street.get(street) == player_name
    
    def has_player_raised(self, player_name: str, street: str) -> bool:
        """
        Check if player has raised on a specific street.
        
        Args:
            player_name: Player's name
            street: The street to check
            
        Returns:
            True if player has raised, False otherwise
        """
        actions = self.get_player_action_types(player_name, street)
        return 'raise' in actions
    
    def has_player_called(self, player_name: str, street: str) -> bool:
        """
        Check if player has called on a specific street.
        
        Args:
            player_name: Player's name
            street: The street to check
            
        Returns:
            True if player has called, False otherwise
        """
        actions = self.get_player_action_types(player_name, street)
        return 'call' in actions
    
    def has_player_checked(self, player_name: str, street: str) -> bool:
        """
        Check if player has checked on a specific street.
        
        Args:
            player_name: Player's name
            street: The street to check
            
        Returns:
            True if player has checked, False otherwise
        """
        actions = self.get_player_action_types(player_name, street)
        return 'check' in actions
    
    def get_player_total_invested(self, player_name: str) -> float:
        """
        Get the total amount invested by a player in this hand.
        
        Args:
            player_name: Player's name
            
        Returns:
            Total amount invested
        """
        total = 0.0
        for street in self.actions_by_street:
            for action in self.actions_by_street[street]:
                if action.player_name == player_name and action.action_type in ['bet', 'call', 'raise']:
                    total += action.amount
        return total
    
    def get_player_action_summary(self, player_name: str) -> Dict[str, List[str]]:
        """
        Get a summary of all actions taken by a player in this hand.
        
        Args:
            player_name: Player's name
            
        Returns:
            Dictionary mapping streets to lists of action types
        """
        summary = {}
        for street in self.actions_by_street:
            actions = self.get_player_action_types(player_name, street)
            if actions:
                summary[street] = actions
        return summary
    
    def get_raises_on_street(self, street: str) -> int:
        """
        Get the number of raises on a specific street.
        
        Args:
            street: The street to check
            
        Returns:
            Number of raises
        """
        return self.raises_by_street.get(street, 0)
    
    def summarize_hand(self) -> str:
        """
        Get a summary of the hand history.
        
        Returns:
            String summarizing the hand history
        """
        summary = [f"Hand ID: {self.hand_id}"]
        
        for street in ["preflop", "flop", "turn", "river"]:
            if self.actions_by_street[street]:
                summary.append(f"\n--- {street.upper()} ---")
                if street in ["flop", "turn", "river"] and self.community_cards.get(street):
                    summary.append(f"Board: {' '.join(self.community_cards.get(street, []))}")
                summary.append(f"Pot: {self.pot_size_by_street.get(street, 0):.2f}")
                
                for action in self.actions_by_street[street]:
                    summary.append(str(action))
        
        return "\n".join(summary)


class HandHistoryTracker:
    """Manages the tracking of hand histories for the poker bot"""
    
    def __init__(self):
        self.current_hand = None
        self.hand_histories = {}  # Map hand_id to HandHistory objects
        self.max_histories = 50  # Maximum number of hand histories to store
    
    def start_new_hand(self, hand_id: str) -> HandHistory:
        """
        Start tracking a new poker hand.
        
        Args:
            hand_id: Unique identifier for the hand
            
        Returns:
            The new HandHistory object
        """
        # Complete previous hand if it exists
        if self.current_hand:
            self.current_hand.complete_hand()
        
        # Create new hand history
        self.current_hand = HandHistory(hand_id)
        self.hand_histories[hand_id] = self.current_hand
        
        # Limit the number of stored hand histories
        if len(self.hand_histories) > self.max_histories:
            oldest_hand_id = next(iter(self.hand_histories))
            del self.hand_histories[oldest_hand_id]
        
        return self.current_hand
    
    def record_action(self, player_name: str, action_type: str, amount: float, 
                     street: str, position: str, hand_id: str = None) -> None:
        """
        Record an action in the current or specified hand.
        
        Args:
            player_name: Name of the player who took the action
            action_type: Type of action (fold, check, call, raise, bet)
            amount: Bet amount (0 for check/fold)
            street: The street on which the action occurred
            position: Player's position
            hand_id: Optional hand ID (defaults to current hand)
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            logger.warning("No active hand to record action")
            return
        
        hand.add_action(player_name, action_type, amount, street, position)
    
    def update_pot_size(self, pot_size: float, street: str, hand_id: str = None) -> None:
        """
        Update the pot size for the current or specified hand.
        
        Args:
            pot_size: Current pot size
            street: The street (preflop, flop, turn, river)
            hand_id: Optional hand ID (defaults to current hand)
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            logger.warning("No active hand to update pot size")
            return
        
        hand.update_pot_size(street, pot_size)
    
    def add_community_cards(self, cards: List[str], street: str, hand_id: str = None) -> None:
        """
        Add community cards for the current or specified hand.
        
        Args:
            cards: List of cards in string format
            street: The street (flop, turn, river)
            hand_id: Optional hand ID (defaults to current hand)
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            logger.warning("No active hand to add community cards")
            return
        
        hand.add_community_cards(street, cards)
    
    def add_player_cards(self, player_name: str, cards: List[str], hand_id: str = None) -> None:
        """
        Add hole cards for a player in the current or specified hand.
        
        Args:
            player_name: Player's name
            cards: List of hole cards
            hand_id: Optional hand ID (defaults to current hand)
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            logger.warning("No active hand to add player cards")
            return
        
        hand.add_player_cards(player_name, cards)
    
    def get_current_hand(self) -> Optional[HandHistory]:
        """
        Get the current hand being tracked.
        
        Returns:
            The current HandHistory object or None if no hand is being tracked
        """
        return self.current_hand
    
    def get_hand_history(self, hand_id: str) -> Optional[HandHistory]:
        """
        Get a specific hand history by its ID.
        
        Args:
            hand_id: The ID of the hand to retrieve
            
        Returns:
            The HandHistory object or None if not found
        """
        return self.hand_histories.get(hand_id)
    
    def is_player_preflop_raiser(self, player_name: str, hand_id: str = None) -> bool:
        """
        Check if player was a preflop raiser in the current or specified hand.
        
        Args:
            player_name: Player's name
            hand_id: Optional hand ID (defaults to current hand)
            
        Returns:
            True if player raised preflop, False otherwise
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            return False
        
        return hand.has_player_raised(player_name, "preflop")
    
    def is_player_aggressor_on_street(self, player_name: str, street: str, hand_id: str = None) -> bool:
        """
        Check if player was the aggressor on a specific street in the current or specified hand.
        
        Args:
            player_name: Player's name
            street: The street to check
            hand_id: Optional hand ID (defaults to current hand)
            
        Returns:
            True if player was the aggressor, False otherwise
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            return False
        
        return hand.is_player_aggressor(player_name, street)
    
    def get_player_action_summary(self, player_name: str, hand_id: str = None) -> Dict[str, List[str]]:
        """
        Get a summary of all actions taken by a player in the current or specified hand.
        
        Args:
            player_name: Player's name
            hand_id: Optional hand ID (defaults to current hand)
            
        Returns:
            Dictionary mapping streets to lists of action types
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            return {}
        
        return hand.get_player_action_summary(player_name)
    
    def get_street_aggression_info(self, player_name: str, hand_id: str = None) -> Dict[str, bool]:
        """
        Get information about a player's aggression across all streets.
        
        Args:
            player_name: Player's name
            hand_id: Optional hand ID (defaults to current hand)
            
        Returns:
            Dictionary mapping streets to boolean indicating if player was aggressor
        """
        if hand_id and hand_id in self.hand_histories:
            hand = self.hand_histories[hand_id]
        elif self.current_hand:
            hand = self.current_hand
        else:
            return {}
        
        return {
            street: hand.is_player_aggressor(player_name, street)
            for street in ["preflop", "flop", "turn", "river"]
        }

# Global tracker instance for easy access across modules
hand_history_tracker = HandHistoryTracker()

def get_hand_history_tracker() -> HandHistoryTracker:
    """
    Get the global hand history tracker instance.
    
    Returns:
        Global HandHistoryTracker instance
    """
    return hand_history_tracker
