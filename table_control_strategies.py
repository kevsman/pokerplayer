# table_control_strategies.py
"""
Advanced table control strategies to make the poker bot more assertive and dominant.
This module implements aggressive tactics for taking control of the table dynamics.
"""

import logging
import random
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class TableControlManager:
    """
    Manages aggressive table control strategies to establish dominance and pressure opponents.
    """
    
    def __init__(self, config=None):
        self.config = config
        self.recent_actions = []  # Track recent aggressive actions
        self.image_establishment_mode = True  # Start aggressively to establish image
        
        # MAXIMUM aggression settings for complete table domination
        self.isolation_threshold = 0.85  # Isolate limpers very frequently
        self.squeeze_threshold = 0.70    # Squeeze multiway pots aggressively
        self.barrel_threshold = 0.80     # Continue bluffing on later streets very often
        self.steal_threshold = 0.90      # Steal blinds from late position almost always
        
    def should_isolate_limpers(self, position: str, limper_count: int, hand_category: str, 
                             stack_size: float, pot_size: float) -> Tuple[bool, float]:
        """
        Determine if we should isolation raise against limpers.
        More aggressive isolation for table control.
        """
        if limper_count == 0:
            return False, 0.0
            
        # Base isolation probability
        isolation_prob = self.isolation_threshold
        
        # Position adjustments - more aggressive from all positions
        position_multipliers = {
            'BTN': 1.3, 'CO': 1.2, 'MP': 1.1, 'UTG': 1.0, 'SB': 1.4, 'BB': 1.1
        }
        isolation_prob *= position_multipliers.get(position, 1.0)
        
        # Hand strength adjustments - widen isolation range significantly
        hand_multipliers = {
            'Premium Pair': 1.0,  # Always isolate
            'Strong Pair': 1.0,   # Always isolate
            'Medium Pair': 0.9,   # Almost always isolate
            'Suited Ace': 0.85,   # Very frequently isolate
            'Suited King': 0.8,   # Frequently isolate
            'Suited Broadway': 0.75,  # Often isolate
            'Offsuit Ace': 0.7,   # Sometimes isolate
            'Suited Connector': 0.65,  # Occasionally isolate for aggression
        }
        isolation_prob *= hand_multipliers.get(hand_category, 0.4)
        
        # Limper count adjustments - more aggressive against multiple limpers
        if limper_count >= 3:
            isolation_prob *= 1.2  # More profitable to isolate multiple fish
        elif limper_count == 2:
            isolation_prob *= 1.1
            
        # Stack depth considerations
        spr = stack_size / pot_size if pot_size > 0 else float('inf')
        if spr > 10:  # Deep stacks - more isolation for control
            isolation_prob *= 1.15
        elif spr < 5:  # Shallow stacks - still isolate but less frequently
            isolation_prob *= 0.9
            
        should_isolate = random.random() < isolation_prob
        
        # Calculate isolation raise size - more aggressive sizing
        if should_isolate:
            base_raise = pot_size * 0.8  # Larger base size
            isolation_size = base_raise + (limper_count * pot_size * 0.3)  # Add for each limper
            isolation_size = min(isolation_size, stack_size)
        else:
            isolation_size = 0.0
            
        logger.info(f"Isolation decision: {should_isolate}, size: {isolation_size:.2f}, "
                   f"prob: {isolation_prob:.2f}, limpers: {limper_count}")
        
        return should_isolate, isolation_size
    
    def should_squeeze_play(self, position: str, opener_position: str, caller_count: int, 
                          hand_category: str, stack_size: float, pot_size: float) -> Tuple[bool, float]:
        """
        Determine if we should make a squeeze play in a multiway pot.
        Aggressive squeezing for table control.
        """
        if caller_count == 0:
            return False, 0.0
            
        # Base squeeze probability
        squeeze_prob = self.squeeze_threshold
        
        # Position adjustments - squeeze more from late position
        if position in ['BTN', 'CO']:
            squeeze_prob *= 1.4
        elif position in ['SB', 'BB']:
            squeeze_prob *= 1.2  # Squeeze from blinds to punish loose calls
        else:
            squeeze_prob *= 0.8
            
        # Opener position adjustments - squeeze more vs late position opens
        if opener_position in ['BTN', 'CO', 'SB']:
            squeeze_prob *= 1.3  # Likely stealing, good squeeze spot
        elif opener_position in ['UTG', 'UTG+1']:
            squeeze_prob *= 0.7  # Stronger range, squeeze less
            
        # Hand strength adjustments for squeezing
        squeeze_hand_multipliers = {
            'Premium Pair': 1.0,
            'Strong Pair': 0.95,
            'Medium Pair': 0.8,
            'Suited Ace': 0.85,  # Good squeeze hands with blockers
            'Suited King': 0.75,
            'Suited Broadway': 0.7,
            'Suited Connector': 0.6,  # Playable squeeze bluffs
        }
        squeeze_prob *= squeeze_hand_multipliers.get(hand_category, 0.3)
        
        # Caller count adjustments - more profitable vs more callers
        squeeze_prob *= (1.0 + caller_count * 0.15)
        
        should_squeeze = random.random() < squeeze_prob
        
        # Calculate squeeze size - large sizing for maximum pressure
        if should_squeeze:
            # Pot contains opener's raise + all calls
            current_pot_estimate = pot_size
            squeeze_size = current_pot_estimate * (2.5 + caller_count * 0.5)  # Very large squeeze
            squeeze_size = min(squeeze_size, stack_size)
        else:
            squeeze_size = 0.0
            
        logger.info(f"Squeeze decision: {should_squeeze}, size: {squeeze_size:.2f}, "
                   f"prob: {squeeze_prob:.2f}, callers: {caller_count}")
        
        return should_squeeze, squeeze_size
    
    def should_continue_barrel(self, street: str, hand_strength: str, win_probability: float,
                             opponent_count: int, pot_size: float, stack_size: float,
                             was_preflop_aggressor: bool, board_texture: str = "unknown") -> Tuple[bool, float]:
        """
        Determine if we should continue barreling (continuation betting) on later streets.
        Very aggressive barreling for maximum pressure.
        """
        if not was_preflop_aggressor:
            return False, 0.0
            
        # Base barrel probability - very high for aggression
        barrel_prob = self.barrel_threshold
        
        # Street adjustments
        street_multipliers = {
            'Flop': 1.0,     # Standard c-bet frequency
            'Turn': 0.8,     # Second barrel
            'River': 0.6     # Third barrel - still aggressive
        }
        barrel_prob *= street_multipliers.get(street, 1.0)
        
        # Hand strength adjustments
        if hand_strength in ['very_strong', 'strong']:
            barrel_prob = 0.95  # Almost always bet for value
        elif hand_strength == 'medium':
            barrel_prob *= 0.9  # Aggressive with medium hands
        elif hand_strength == 'drawing':
            barrel_prob *= 0.85  # Semi-bluff frequently
        else:  # weak hands
            barrel_prob *= 0.7  # Still bluff frequently for table control
            
        # Win probability adjustments
        if win_probability > 0.6:
            barrel_prob = 0.95
        elif win_probability > 0.4:
            barrel_prob *= 1.0
        elif win_probability > 0.25:
            barrel_prob *= 0.9  # Still bet draws aggressively
        else:
            barrel_prob *= 0.6  # Pure bluffs
            
        # Opponent count adjustments
        if opponent_count == 1:
            barrel_prob *= 1.2  # More aggressive heads-up
        elif opponent_count == 2:
            barrel_prob *= 1.0
        else:
            barrel_prob *= 0.8  # Slightly less vs multiple opponents
            
        # Board texture adjustments (if available)
        if board_texture == "dry":
            barrel_prob *= 1.15  # More bluffs on dry boards
        elif board_texture == "wet":
            barrel_prob *= 0.9   # Slightly fewer bluffs on wet boards
            
        should_barrel = random.random() < barrel_prob
        
        # Calculate barrel size - aggressive sizing
        if should_barrel:
            if hand_strength in ['very_strong', 'strong']:
                barrel_size = pot_size * 0.8  # Large value bets
            elif hand_strength == 'medium':
                barrel_size = pot_size * 0.7  # Aggressive medium bets
            else:
                barrel_size = pot_size * 0.65 # Substantial bluffs
                
            barrel_size = min(barrel_size, stack_size)
        else:
            barrel_size = 0.0
            
        logger.info(f"Barrel decision ({street}): {should_barrel}, size: {barrel_size:.2f}, "
                   f"prob: {barrel_prob:.2f}, hand: {hand_strength}")
        
        return should_barrel, barrel_size
    
    def should_steal_blinds(self, position: str, hand_category: str, fold_to_steal_stats: Dict,
                          stack_size: float, big_blind: float) -> Tuple[bool, float]:
        """
        Determine if we should attempt to steal blinds from late position.
        Very aggressive blind stealing for table control.
        """
        if position not in ['CO', 'BTN', 'SB']:
            return False, 0.0
            
        # Base steal probability - very high
        steal_prob = self.steal_threshold
        
        # Position adjustments
        position_multipliers = {
            'BTN': 1.0,   # Standard button steal
            'CO': 0.9,    # Cutoff steal
            'SB': 0.85    # Small blind complete/steal vs BB
        }
        steal_prob *= position_multipliers.get(position, 1.0)
        
        # Hand requirements - very wide stealing range for aggression
        steal_hand_multipliers = {
            'Premium Pair': 1.0,
            'Strong Pair': 1.0,
            'Medium Pair': 1.0,
            'Suited Ace': 1.0,
            'Offsuit Ace': 0.95,
            'Suited King': 0.9,
            'Suited Queen': 0.85,
            'Suited Broadway': 0.8,
            'Suited Connector': 0.75,
            'Offsuit Broadway': 0.7,
        }
        steal_prob *= steal_hand_multipliers.get(hand_category, 0.6)  # Even steal with junk sometimes
        
        # Adjust based on blind defenders' tendencies
        bb_fold_to_steal = fold_to_steal_stats.get('BB', 0.7)  # Default assume they fold 70%
        sb_fold_to_steal = fold_to_steal_stats.get('SB', 0.8)  # SB folds more often
        
        if position == 'BTN':
            # Need both blinds to fold
            combined_fold_prob = bb_fold_to_steal * sb_fold_to_steal
            steal_prob *= (0.5 + combined_fold_prob)  # Weight heavily on fold probability
        elif position == 'CO':
            # Button and blinds need to fold
            steal_prob *= 0.8  # More players to act, reduce frequency
        elif position == 'SB':
            # Only BB needs to fold
            steal_prob *= (0.3 + bb_fold_to_steal * 0.7)
            
        should_steal = random.random() < steal_prob
        
        # Calculate steal size - larger steals for more pressure
        if should_steal:
            if position == 'SB':
                steal_size = big_blind * 3.5  # Complete/raise from SB
            else:
                steal_size = big_blind * 2.8  # Standard late position raise
                
            steal_size = min(steal_size, stack_size)
        else:
            steal_size = 0.0
            
        logger.info(f"Steal decision ({position}): {should_steal}, size: {steal_size:.2f}, "
                   f"prob: {steal_prob:.2f}")
        
        return should_steal, steal_size
    
    def adjust_for_table_image(self, base_aggression: float, recent_aggressive_actions: int,
                             table_perception: str = "unknown") -> float:
        """
        Adjust aggression based on table image and recent actions.
        Maintain aggressive image while avoiding becoming too predictable.
        """
        # If we've been very aggressive recently, occasionally dial it back slightly
        if recent_aggressive_actions >= 5:
            # Still stay aggressive but add some unpredictability
            if random.random() < 0.2:  # 20% chance to slow down slightly
                adjustment = 0.85
                logger.info("Slightly reducing aggression for image balance")
            else:
                adjustment = 0.95  # Stay mostly aggressive
        elif recent_aggressive_actions <= 1:
            # Ramp up aggression if we've been too passive
            adjustment = 1.15
            logger.info("Increasing aggression to establish/maintain image")
        else:
            adjustment = 1.0
            
        # Table perception adjustments
        if table_perception == "tight":
            adjustment *= 1.1  # More aggression vs tight players
        elif table_perception == "loose":
            adjustment *= 0.95  # Slightly less vs loose/aggressive table
            
        adjusted_aggression = base_aggression * adjustment
        logger.debug(f"Aggression adjustment: {base_aggression:.2f} -> {adjusted_aggression:.2f}")
        
        return adjusted_aggression
    
    def get_table_control_recommendation(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get overall table control recommendation based on current situation.
        """
        recommendations = {
            'increase_aggression': False,
            'isolation_play': False,
            'squeeze_play': False,
            'steal_attempt': False,
            'barrel_bluff': False,
            'recommended_sizing_multiplier': 1.0,
            'reasoning': []
        }
        
        position = situation.get('position', 'Unknown')
        hand_category = situation.get('hand_category', 'Unknown')
        opponent_count = situation.get('opponent_count', 1)
        stack_size = situation.get('stack_size', 100)
        pot_size = situation.get('pot_size', 0)
        
        # Check for isolation opportunities
        limper_count = situation.get('limper_count', 0)
        if limper_count > 0:
            should_iso, iso_size = self.should_isolate_limpers(
                position, limper_count, hand_category, stack_size, pot_size
            )
            if should_iso:
                recommendations['isolation_play'] = True
                recommendations['recommended_sizing_multiplier'] = iso_size / pot_size if pot_size > 0 else 3.0
                recommendations['reasoning'].append(f"Isolation vs {limper_count} limpers")
        
        # Check for squeeze opportunities
        opener_pos = situation.get('opener_position')
        caller_count = situation.get('caller_count', 0)
        if opener_pos and caller_count > 0:
            should_squeeze, squeeze_size = self.should_squeeze_play(
                position, opener_pos, caller_count, hand_category, stack_size, pot_size
            )
            if should_squeeze:
                recommendations['squeeze_play'] = True
                recommendations['recommended_sizing_multiplier'] = squeeze_size / pot_size if pot_size > 0 else 4.0
                recommendations['reasoning'].append(f"Squeeze vs opener+{caller_count} callers")
        
        # Check for steal opportunities
        if position in ['CO', 'BTN', 'SB'] and opponent_count <= 2:
            fold_stats = situation.get('fold_to_steal_stats', {})
            should_steal, steal_size = self.should_steal_blinds(
                position, hand_category, fold_stats, stack_size, situation.get('big_blind', 1)
            )
            if should_steal:
                recommendations['steal_attempt'] = True
                recommendations['reasoning'].append(f"Blind steal from {position}")
        
        # General aggression recommendation
        if any([recommendations['isolation_play'], recommendations['squeeze_play'], 
                recommendations['steal_attempt']]):
            recommendations['increase_aggression'] = True
            
        return recommendations


def get_enhanced_aggression_factor(config, position: str, situation: Dict[str, Any]) -> float:
    """
    Calculate enhanced aggression factor for the current situation.
    """
    base_factor = config.get_setting('strategy', {}).get('base_aggression_factor_postflop', 2.5)
    
    # Position multipliers
    position_multipliers = config.get_setting('strategy', {}).get('position_aggression_multipliers', {
        'BTN': 1.8, 'CO': 1.6, 'MP': 1.3, 'UTG': 1.1, 'SB': 1.4, 'BB': 1.2
    })
    
    position_factor = position_multipliers.get(position, 1.0)
    
    # Table control mode bonus
    table_control_bonus = 0.3 if config.get_setting('strategy', {}).get('table_control_mode', False) else 0.0
    
    enhanced_factor = base_factor * position_factor + table_control_bonus
    
    logger.debug(f"Enhanced aggression factor: base={base_factor}, position={position_factor}, "
                f"control_bonus={table_control_bonus}, final={enhanced_factor}")
    
    return enhanced_factor
