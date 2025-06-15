# adaptive_timing_controller.py
"""
Adaptive timing controller to optimize parsing frequency and reduce redundant operations.
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class GameStateSnapshot:
    """Snapshot of game state for change detection."""
    hand_id: Optional[str]
    pot_size: float
    active_player: Optional[str]
    game_stage: str
    my_turn: bool
    actions_available: int
    timestamp: float

class AdaptiveTimingController:
    """Controls parsing timing based on game state and activity."""
    
    def __init__(self):
        self.last_state: Optional[GameStateSnapshot] = None
        self.last_parse_time = 0.0
        self.last_action_time = 0.0
        self.consecutive_identical_states = 0
        self.activity_history = deque(maxlen=20)
        self.parse_failures = 0
        
        # Timing configurations
        self.base_delay = 0.5  # Base delay between parses
        self.max_delay = 5.0   # Maximum delay when inactive
        self.min_delay = 0.1   # Minimum delay when active
        self.action_urgency_window = 10.0  # Seconds after action for fast polling
        
    def should_parse_now(self, current_state: Optional[GameStateSnapshot] = None) -> bool:
        """Determine if we should parse HTML now."""
        current_time = time.time()
        
        # Always parse if enough time has passed
        time_since_last = current_time - self.last_parse_time
        if time_since_last < self.min_delay:
            return False
            
        # Fast polling if we expect our turn soon
        if self._is_high_activity_period():
            return time_since_last >= self.min_delay
            
        # Check if state has changed significantly
        if current_state and self.last_state:
            if self._has_significant_change(current_state, self.last_state):
                return True
                
        # Adaptive delay based on activity
        required_delay = self._calculate_adaptive_delay()
        return time_since_last >= required_delay
        
    def record_parse_result(self, state: GameStateSnapshot, success: bool):
        """Record the result of a parsing attempt."""
        self.last_parse_time = time.time()
        
        if success:
            self.parse_failures = 0
            if self.last_state:
                if self._states_identical(state, self.last_state):
                    self.consecutive_identical_states += 1
                else:
                    self.consecutive_identical_states = 0
            self.last_state = state
        else:
            self.parse_failures += 1
            
        # Record activity
        activity_score = self._calculate_activity_score(state)
        self.activity_history.append((time.time(), activity_score))
        
    def record_action_taken(self):
        """Record that an action was taken."""
        self.last_action_time = time.time()
        self.consecutive_identical_states = 0
        
    def get_recommended_delay(self) -> float:
        """Get recommended delay before next parse."""
        return self._calculate_adaptive_delay()
        
    def _has_significant_change(self, current: GameStateSnapshot, previous: GameStateSnapshot) -> bool:
        """Check if there's a significant change between states."""
        return (
            current.hand_id != previous.hand_id or
            current.my_turn != previous.my_turn or
            current.actions_available != previous.actions_available or
            abs(current.pot_size - previous.pot_size) > 0.01 or
            current.active_player != previous.active_player or
            current.game_stage != previous.game_stage
        )
        
    def _states_identical(self, current: GameStateSnapshot, previous: GameStateSnapshot) -> bool:
        """Check if two states are identical."""
        return (
            current.hand_id == previous.hand_id and
            current.pot_size == previous.pot_size and
            current.active_player == previous.active_player and
            current.game_stage == previous.game_stage and
            current.my_turn == previous.my_turn and
            current.actions_available == previous.actions_available
        )
        
    def _is_high_activity_period(self) -> bool:
        """Determine if we're in a high activity period."""
        current_time = time.time()
        
        # High activity if recent action
        if current_time - self.last_action_time < self.action_urgency_window:
            return True
            
        # High activity if recent state changes
        if len(self.activity_history) >= 3:
            recent_activity = sum(score for _, score in list(self.activity_history)[-3:])
            return recent_activity > 1.5
            
        return False
        
    def _calculate_activity_score(self, state: GameStateSnapshot) -> float:
        """Calculate activity score for current state."""
        score = 0.0
        
        if state.my_turn:
            score += 2.0
        if state.actions_available > 0:
            score += 1.0
        if self.last_state and state.hand_id != self.last_state.hand_id:
            score += 1.5  # New hand
        if self.last_state and state.game_stage != self.last_state.game_stage:
            score += 1.0  # New street
            
        return score
        
    def _calculate_adaptive_delay(self) -> float:
        """Calculate adaptive delay based on current conditions."""
        base = self.base_delay
        
        # Increase delay for consecutive identical states
        if self.consecutive_identical_states > 5:
            base *= (1 + self.consecutive_identical_states * 0.2)
            
        # Decrease delay during high activity
        if self._is_high_activity_period():
            base *= 0.3
            
        # Increase delay after parse failures
        if self.parse_failures > 0:
            base *= (1 + self.parse_failures * 0.5)
            
        return max(self.min_delay, min(self.max_delay, base))

def create_adaptive_timing_controller() -> AdaptiveTimingController:
    """Factory function to create timing controller."""
    return AdaptiveTimingController()
