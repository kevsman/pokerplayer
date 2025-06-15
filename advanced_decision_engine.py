# advanced_decision_engine.py
"""
Advanced decision engine with sophisticated strategy, opponent modeling, and adaptive play.
"""

import logging
import random
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PlayingStyle(Enum):
    TIGHT_PASSIVE = "tight_passive"
    TIGHT_AGGRESSIVE = "tight_aggressive"
    LOOSE_PASSIVE = "loose_passive"
    LOOSE_AGGRESSIVE = "loose_aggressive"
    UNKNOWN = "unknown"

class BoardTexture(Enum):
    DRY = "dry"
    WET = "wet"
    COORDINATED = "coordinated"
    RAINBOW = "rainbow"

@dataclass
class OpponentProfile:
    """Profile of an opponent's playing style."""
    name: str
    vpip: float = 0.0  # Voluntarily Put $ In Pot
    pfr: float = 0.0   # Pre-Flop Raise
    aggression_factor: float = 1.0
    fold_to_cbet: float = 0.0
    fold_to_3bet: float = 0.0
    hands_observed: int = 0
    style: PlayingStyle = PlayingStyle.UNKNOWN
    stack_size: float = 0.0
    
    def update_stats(self, action: str, street: str, was_aggressor: bool):
        """Update opponent statistics based on observed action."""
        self.hands_observed += 1
        
        # Update VPIP (any voluntary money in pot)
        if action in ['call', 'raise', 'bet'] and street == 'preflop':
            self.vpip = (self.vpip * (self.hands_observed - 1) + 1) / self.hands_observed
        elif street == 'preflop':
            self.vpip = (self.vpip * (self.hands_observed - 1)) / self.hands_observed
            
        # Update PFR (preflop raising)
        if action in ['raise', 'bet'] and street == 'preflop':
            self.pfr = (self.pfr * (self.hands_observed - 1) + 1) / self.hands_observed
        elif street == 'preflop':
            self.pfr = (self.pfr * (self.hands_observed - 1)) / self.hands_observed
            
        # Update aggression factor
        if action in ['bet', 'raise']:
            self.aggression_factor = min(5.0, self.aggression_factor * 1.1)
        elif action == 'call':
            self.aggression_factor = max(0.2, self.aggression_factor * 0.95)
            
        # Classify playing style
        self._classify_style()
        
    def _classify_style(self):
        """Classify opponent's playing style based on stats."""
        if self.hands_observed < 5:
            self.style = PlayingStyle.UNKNOWN
            return
            
        is_tight = self.vpip < 0.25
        is_aggressive = self.aggression_factor > 1.5
        
        if is_tight and is_aggressive:
            self.style = PlayingStyle.TIGHT_AGGRESSIVE
        elif is_tight and not is_aggressive:
            self.style = PlayingStyle.TIGHT_PASSIVE
        elif not is_tight and is_aggressive:
            self.style = PlayingStyle.LOOSE_AGGRESSIVE
        else:
            self.style = PlayingStyle.LOOSE_PASSIVE

@dataclass
class DecisionContext:
    """Context information for making decisions."""
    hand_strength: str
    position: str
    pot_size: float
    bet_to_call: float
    stack_size: float
    pot_odds: float
    win_probability: float
    opponents: List[OpponentProfile]
    board_texture: BoardTexture
    street: str
    spr: float  # Stack-to-Pot Ratio
    actions_available: List[str]
    betting_history: List[Dict]
    
class AdvancedDecisionEngine:
    """Advanced decision engine with sophisticated strategy."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Strategy parameters
        self.base_aggression = self.config.get('base_aggression', 1.0)
        self.bluff_frequency = self.config.get('bluff_frequency', 0.15)
        self.value_bet_threshold = self.config.get('value_bet_threshold', 0.65)
        self.fold_threshold = self.config.get('fold_threshold', 0.25)
        
        # Position adjustments
        self.position_multipliers = {
            'BTN': 1.3,    # Button - most aggressive
            'CO': 1.2,     # Cutoff
            'MP': 1.0,     # Middle position
            'UTG': 0.8,    # Under the gun - most conservative
            'SB': 0.9,     # Small blind
            'BB': 1.1      # Big blind - slightly loose
        }
        
    def make_advanced_decision(self, context: DecisionContext) -> Tuple[str, float, str]:
        """
        Make an advanced decision based on comprehensive analysis.
        Returns (action, amount, reasoning)
        """
        try:
            # Analyze situation
            situation_analysis = self._analyze_situation(context)
            
            # Get base decision from multiple strategies
            strategies = [
                self._gto_strategy(context, situation_analysis),
                self._exploitative_strategy(context, situation_analysis),
                self._spr_strategy(context, situation_analysis)
            ]
            
            # Combine strategies
            final_decision = self._combine_strategies(strategies, context)
            
            # Apply position and opponent adjustments
            adjusted_decision = self._apply_adjustments(final_decision, context)
            
            # Validate and execute
            action, amount, reasoning = self._validate_decision(adjusted_decision, context)
            
            self.logger.info(f"Advanced decision: {action} {amount:.2f} - {reasoning}")
            
            return action, amount, reasoning
            
        except Exception as e:
            self.logger.error(f"Error in advanced decision making: {e}")
            return 'fold', 0.0, 'Error fallback'
            
    def _analyze_situation(self, context: DecisionContext) -> Dict:
        """Analyze the current situation comprehensively."""
        analysis = {
            'hand_category': self._categorize_hand_strength(context.hand_strength, context.win_probability),
            'pot_commitment': context.stack_size / (context.pot_size + context.bet_to_call) if context.pot_size > 0 else float('inf'),
            'position_advantage': self._assess_position_advantage(context.position),
            'opponent_tendencies': self._analyze_opponents(context.opponents),
            'board_danger': self._assess_board_danger(context.board_texture, context.street),
            'betting_pattern': self._analyze_betting_pattern(context.betting_history),
            'stack_pressure': self._assess_stack_pressure(context.spr),
            'implied_odds': self._calculate_implied_odds(context)
        }
        
        return analysis
        
    def _categorize_hand_strength(self, hand_strength: str, win_prob: float) -> str:
        """Categorize hand strength more precisely."""
        if win_prob >= 0.85:
            return 'nuts'
        elif win_prob >= 0.75:
            return 'very_strong'
        elif win_prob >= 0.65:
            return 'strong'
        elif win_prob >= 0.55:
            return 'medium_strong'
        elif win_prob >= 0.45:
            return 'medium'
        elif win_prob >= 0.35:
            return 'weak_made'
        elif win_prob >= 0.25:
            return 'draw'
        else:
            return 'trash'
            
    def _gto_strategy(self, context: DecisionContext, analysis: Dict) -> Dict:
        """Game Theory Optimal strategy baseline."""
        hand_category = analysis['hand_category']
        
        if hand_category in ['nuts', 'very_strong']:
            # Value bet/raise aggressively
            bet_size = self._calculate_value_bet_size(context, 0.8)
            return {'action': 'raise', 'amount': bet_size, 'confidence': 0.9}
            
        elif hand_category in ['strong', 'medium_strong']:
            # Value bet smaller or call
            if context.bet_to_call == 0:  # We can bet
                bet_size = self._calculate_value_bet_size(context, 0.6)
                return {'action': 'raise', 'amount': bet_size, 'confidence': 0.7}
            else:
                if context.pot_odds < context.win_probability:
                    return {'action': 'call', 'amount': context.bet_to_call, 'confidence': 0.8}
                else:
                    return {'action': 'fold', 'amount': 0, 'confidence': 0.6}
                    
        elif hand_category == 'medium':
            # Check/call or small bet
            if context.bet_to_call == 0:
                if random.random() < 0.3:  # Occasional bluff
                    bet_size = context.pot_size * 0.4
                    return {'action': 'raise', 'amount': bet_size, 'confidence': 0.4}
                else:
                    return {'action': 'check', 'amount': 0, 'confidence': 0.6}
            else:
                if context.pot_odds < context.win_probability:
                    return {'action': 'call', 'amount': context.bet_to_call, 'confidence': 0.5}
                else:
                    return {'action': 'fold', 'amount': 0, 'confidence': 0.7}
                    
        elif hand_category in ['draw']:
            # Semi-bluff or call with draws
            if context.bet_to_call == 0:
                if random.random() < 0.4:  # Semi-bluff
                    bet_size = context.pot_size * 0.5
                    return {'action': 'raise', 'amount': bet_size, 'confidence': 0.5}
                else:
                    return {'action': 'check', 'amount': 0, 'confidence': 0.7}
            else:
                implied_odds = analysis['implied_odds']
                if implied_odds > context.pot_odds:
                    return {'action': 'call', 'amount': context.bet_to_call, 'confidence': 0.6}
                else:
                    return {'action': 'fold', 'amount': 0, 'confidence': 0.8}
        else:
            # Weak hands - mostly fold
            if context.bet_to_call == 0 and random.random() < self.bluff_frequency:
                bet_size = context.pot_size * 0.6
                return {'action': 'raise', 'amount': bet_size, 'confidence': 0.3}
            else:
                return {'action': 'fold', 'amount': 0, 'confidence': 0.9}
                
    def _exploitative_strategy(self, context: DecisionContext, analysis: Dict) -> Dict:
        """Strategy that exploits opponent tendencies."""
        opponent_tendencies = analysis['opponent_tendencies']
        
        # Exploit tight players by bluffing more
        if opponent_tendencies.get('avg_fold_frequency', 0.5) > 0.6:
            bluff_multiplier = 1.5
        else:
            bluff_multiplier = 0.7
            
        # Exploit loose players by value betting wider
        if opponent_tendencies.get('avg_vpip', 0.25) > 0.4:
            value_threshold = 0.55  # Lower threshold for value betting
        else:
            value_threshold = 0.65  # Higher threshold against tight players
            
        # Apply exploitative adjustments to GTO baseline
        gto_decision = self._gto_strategy(context, analysis)
        
        if gto_decision['action'] == 'raise' and 'bluff' in str(analysis.get('hand_category', '')):
            gto_decision['amount'] *= bluff_multiplier
            gto_decision['confidence'] *= bluff_multiplier
            
        return gto_decision
        
    def _spr_strategy(self, context: DecisionContext, analysis: Dict) -> Dict:
        """Stack-to-Pot Ratio based strategy."""
        spr = context.spr
        stack_pressure = analysis['stack_pressure']
        
        if spr <= 1.5:  # Low SPR - commit with decent hands
            if context.win_probability > 0.4:
                return {'action': 'raise', 'amount': context.stack_size, 'confidence': 0.8}
            else:
                return {'action': 'fold', 'amount': 0, 'confidence': 0.7}
                
        elif spr <= 4:  # Medium SPR - be selective
            if context.win_probability > 0.6:
                bet_size = min(context.stack_size, context.pot_size * 0.8)
                return {'action': 'raise', 'amount': bet_size, 'confidence': 0.7}
            elif context.win_probability > 0.45:
                return {'action': 'call', 'amount': context.bet_to_call, 'confidence': 0.6}
            else:
                return {'action': 'fold', 'amount': 0, 'confidence': 0.8}
                
        else:  # High SPR - play more conservatively
            if context.win_probability > 0.7:
                bet_size = context.pot_size * 0.6
                return {'action': 'raise', 'amount': bet_size, 'confidence': 0.8}
            elif context.win_probability > 0.5:
                return {'action': 'call', 'amount': context.bet_to_call, 'confidence': 0.7}
            else:
                return {'action': 'fold', 'amount': 0, 'confidence': 0.8}
                
    def _combine_strategies(self, strategies: List[Dict], context: DecisionContext) -> Dict:
        """Combine multiple strategies into final decision."""
        if not strategies:
            return {'action': 'fold', 'amount': 0, 'confidence': 0.5}
            
        # Weight strategies by confidence and street
        weights = [1.0, 1.2, 0.8]  # GTO, Exploitative, SPR
        
        if context.street == 'preflop':
            weights = [0.8, 1.0, 1.5]  # Emphasize SPR preflop
        elif context.street == 'river':
            weights = [1.2, 1.5, 0.8]  # Emphasize exploitation on river
            
        # Weighted voting
        action_votes = {}
        total_weight = 0
        
        for i, strategy in enumerate(strategies):
            action = strategy['action']
            confidence = strategy['confidence']
            weight = weights[i] * confidence
            
            if action not in action_votes:
                action_votes[action] = {'weight': 0, 'amounts': [], 'confidences': []}
                
            action_votes[action]['weight'] += weight
            action_votes[action]['amounts'].append(strategy['amount'])
            action_votes[action]['confidences'].append(confidence)
            total_weight += weight
            
        # Select winning action
        best_action = max(action_votes.keys(), key=lambda x: action_votes[x]['weight'])
        best_data = action_votes[best_action]
        
        # Average amount and confidence
        avg_amount = sum(best_data['amounts']) / len(best_data['amounts'])
        avg_confidence = sum(best_data['confidences']) / len(best_data['confidences'])
        
        return {
            'action': best_action,
            'amount': avg_amount,
            'confidence': avg_confidence
        }
        
    def _apply_adjustments(self, decision: Dict, context: DecisionContext) -> Dict:
        """Apply position and opponent adjustments."""
        # Position adjustment
        position_mult = self.position_multipliers.get(context.position, 1.0)
        
        if decision['action'] == 'raise':
            decision['amount'] *= position_mult
            
        # Stack size adjustment
        if decision['amount'] > context.stack_size * 0.8:
            decision['amount'] = context.stack_size  # Go all-in
            
        # Minimum bet size
        if decision['action'] == 'raise' and decision['amount'] < context.pot_size * 0.3:
            decision['amount'] = context.pot_size * 0.3
            
        return decision
        
    def _validate_decision(self, decision: Dict, context: DecisionContext) -> Tuple[str, float, str]:
        """Validate and finalize decision."""
        action = decision['action']
        amount = decision['amount']
        confidence = decision['confidence']
        
        # Ensure action is available
        if action not in context.actions_available:
            if 'check' in context.actions_available:
                action = 'check'
                amount = 0
            elif 'call' in context.actions_available:
                action = 'call'
                amount = context.bet_to_call
            else:
                action = 'fold'
                amount = 0
                
        # Validate amount
        if action == 'call':
            amount = context.bet_to_call
        elif action in ['check', 'fold']:
            amount = 0
        elif action == 'raise':
            amount = min(amount, context.stack_size)
            
        # Generate reasoning
        reasoning = f"Advanced strategy (confidence: {confidence:.2f})"
        
        return action, amount, reasoning
        
    # Helper methods
    def _assess_position_advantage(self, position: str) -> float:
        """Assess positional advantage."""
        position_scores = {
            'BTN': 1.0,
            'CO': 0.8,
            'MP': 0.6,
            'UTG': 0.3,
            'SB': 0.4,
            'BB': 0.5
        }
        return position_scores.get(position, 0.5)
        
    def _analyze_opponents(self, opponents: List[OpponentProfile]) -> Dict:
        """Analyze opponent tendencies."""
        if not opponents:
            return {'avg_vpip': 0.25, 'avg_aggression': 1.0, 'avg_fold_frequency': 0.5}
            
        total_vpip = sum(opp.vpip for opp in opponents if opp.hands_observed > 0)
        total_aggression = sum(opp.aggression_factor for opp in opponents)
        
        return {
            'avg_vpip': total_vpip / len(opponents) if opponents else 0.25,
            'avg_aggression': total_aggression / len(opponents) if opponents else 1.0,
            'avg_fold_frequency': 0.5,  # Default
            'tight_opponents': sum(1 for opp in opponents if opp.style in [PlayingStyle.TIGHT_PASSIVE, PlayingStyle.TIGHT_AGGRESSIVE]),
            'aggressive_opponents': sum(1 for opp in opponents if opp.style in [PlayingStyle.TIGHT_AGGRESSIVE, PlayingStyle.LOOSE_AGGRESSIVE])
        }
        
    def _assess_board_danger(self, board_texture: BoardTexture, street: str) -> float:
        """Assess how dangerous the board is."""
        danger_scores = {
            BoardTexture.DRY: 0.2,
            BoardTexture.WET: 0.8,
            BoardTexture.COORDINATED: 0.9,
            BoardTexture.RAINBOW: 0.3
        }
        
        base_danger = danger_scores.get(board_texture, 0.5)
        
        # Increase danger as streets progress
        street_multipliers = {
            'preflop': 0.5,
            'flop': 1.0,
            'turn': 1.2,
            'river': 1.0
        }
        
        return base_danger * street_multipliers.get(street, 1.0)
        
    def _analyze_betting_pattern(self, betting_history: List[Dict]) -> Dict:
        """Analyze betting patterns."""
        if not betting_history:
            return {'aggression_level': 'normal', 'bet_sizing': 'normal'}
            
        # Analyze recent betting
        recent_bets = betting_history[-5:]  # Last 5 actions
        
        aggressive_actions = sum(1 for action in recent_bets if action.get('action_type') in ['bet', 'raise'])
        total_actions = len(recent_bets)
        
        aggression_ratio = aggressive_actions / total_actions if total_actions > 0 else 0
        
        if aggression_ratio > 0.7:
            aggression_level = 'high'
        elif aggression_ratio > 0.4:
            aggression_level = 'medium'
        else:
            aggression_level = 'low'
            
        return {
            'aggression_level': aggression_level,
            'bet_sizing': 'normal',  # Could be enhanced
            'pattern_reliability': min(1.0, total_actions / 10.0)
        }
        
    def _assess_stack_pressure(self, spr: float) -> float:
        """Assess stack pressure based on SPR."""
        if spr <= 1:
            return 1.0  # High pressure
        elif spr <= 3:
            return 0.7  # Medium pressure
        elif spr <= 8:
            return 0.4  # Low pressure
        else:
            return 0.1  # Very low pressure
            
    def _calculate_implied_odds(self, context: DecisionContext) -> float:
        """Calculate implied odds for drawing hands."""
        if context.street == 'river':
            return context.pot_odds  # No future betting
            
        # Estimate additional money we can win
        opponent_stacks = sum(opp.stack_size for opp in context.opponents)
        potential_winnings = min(opponent_stacks * 0.3, context.stack_size)
        
        implied_pot = context.pot_size + potential_winnings
        implied_odds = context.bet_to_call / implied_pot if implied_pot > 0 else 1.0
        
        return implied_odds
        
    def _calculate_value_bet_size(self, context: DecisionContext, aggression: float) -> float:
        """Calculate optimal value bet size."""
        base_size = context.pot_size * (0.5 + aggression * 0.3)
        
        # Adjust for opponent tendencies
        if len(context.opponents) > 0:
            avg_fold_frequency = 0.5  # Default
            # Bet smaller against calling stations, larger against nits
            size_multiplier = 0.7 + (avg_fold_frequency * 0.6)
            base_size *= size_multiplier
            
        return min(base_size, context.stack_size)

def create_advanced_decision_engine(config: Dict = None) -> AdvancedDecisionEngine:
    """Factory function to create advanced decision engine."""
    return AdvancedDecisionEngine(config)
