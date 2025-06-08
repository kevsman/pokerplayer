# cash_game_enhancements.py
"""
Next-level cash game specific improvements for the poker bot.
Focus areas: position-based play, stack depth optimization, river play improvements,
thin value betting, and exploitative adjustments.
"""

import logging
import math

logger = logging.getLogger(__name__)

class CashGameEnhancer:
    """
    Enhanced cash game decision making with advanced position-based play,
    stack depth considerations, and exploitative adjustments.
    """
    
    def __init__(self):
        self.position_rankings = {
            'UTG': 1, 'UTG+1': 2, 'MP': 3, 'MP+1': 4, 'LJ': 5,
            'HJ': 6, 'CO': 7, 'BTN': 8, 'SB': 9, 'BB': 10
        }
        
    def get_position_based_adjustments(self, position, street, hand_strength, 
                                      active_opponents_count, stack_depth_bb):
        """
        Get position-based adjustments for cash game play.
        
        Args:
            position: Player position (e.g., 'BTN', 'CO', 'EP')
            street: Current street ('flop', 'turn', 'river')
            hand_strength: Hand strength classification
            active_opponents_count: Number of active opponents
            stack_depth_bb: Stack depth in big blinds
            
        Returns:
            dict: Position-based adjustments for aggression, bet sizing, and frequency
        """
        try:
            position_rank = self.position_rankings.get(position, 5)
            
            # Base adjustments by position
            if position in ['BTN', 'CO']:  # Late position
                aggression_multiplier = 1.15
                bluff_frequency_multiplier = 1.3
                value_sizing_multiplier = 1.1
                thin_value_threshold = 0.55  # Can bet thinner
                
            elif position in ['HJ', 'LJ', 'MP+1']:  # Middle position  
                aggression_multiplier = 1.0
                bluff_frequency_multiplier = 1.0
                value_sizing_multiplier = 1.0
                thin_value_threshold = 0.60
                
            else:  # Early position or blinds
                aggression_multiplier = 0.9
                bluff_frequency_multiplier = 0.8
                value_sizing_multiplier = 0.95
                thin_value_threshold = 0.65  # Need stronger hands
            
            # Street-specific adjustments
            if street == 'river':
                # Late position gets more aggressive on river
                if position in ['BTN', 'CO']:
                    aggression_multiplier *= 1.2
                    thin_value_threshold -= 0.05  # Even thinner value bets
            
            # Multiway adjustments
            if active_opponents_count > 2:
                aggression_multiplier *= 0.85
                thin_value_threshold += 0.05
                
            # Stack depth considerations
            if stack_depth_bb > 150:  # Deep stacks
                bluff_frequency_multiplier *= 1.1
                if position in ['BTN', 'CO']:
                    aggression_multiplier *= 1.05
            elif stack_depth_bb < 50:  # Short stacks
                aggression_multiplier *= 1.1  # More direct play
                bluff_frequency_multiplier *= 0.8
            
            return {
                'aggression_multiplier': aggression_multiplier,
                'bluff_frequency_multiplier': bluff_frequency_multiplier,
                'value_sizing_multiplier': value_sizing_multiplier,
                'thin_value_threshold': thin_value_threshold,
                'position_rank': position_rank,
                'reasoning': f'pos_{position}_street_{street}_opponents_{active_opponents_count}'
            }
            
        except Exception as e:
            logger.warning(f"Error in position adjustments: {e}")
            return {
                'aggression_multiplier': 1.0,                'bluff_frequency_multiplier': 1.0,
                'value_sizing_multiplier': 1.0,
                'thin_value_threshold': 0.60,
                'position_rank': 5,
                'reasoning': 'fallback_position_adjustments'
            }

    def get_stack_depth_strategy(self, stack_depth_bb, effective_stack_bb, pot_size, big_blind):
        """
        Get strategy adjustments based on stack depth for cash games.
        
        Args:
            stack_depth_bb: Our stack in big blinds
            effective_stack_bb: Effective stack depth
            pot_size: Current pot size
            big_blind: Big blind amount
            
        Returns:
            dict: Stack depth strategy adjustments
        """
        try:
            spr = effective_stack_bb / (pot_size / big_blind) if pot_size > 0 else effective_stack_bb / 3
            
            if effective_stack_bb > 150:  # Deep stack play (>150bb)
                strategy = {
                    'strategy_type': 'deep_stack',
                    'category': 'deep_stack',
                    'implied_odds_multiplier': 1.3,
                    'set_mining_threshold': 0.15,  # Will call up to 15:1 for sets
                    'speculative_hands_bonus': 0.1,
                    'bet_sizing_preference': 0.65,  # Smaller bets, more streets
                    'bluff_frequency_bonus': 0.1,
                    'postflop_aggression': 1.1,
                    'drawing_hand_liberality': 1.2
                }
                
            elif effective_stack_bb > 80:  # Standard stack (80-150bb)
                strategy = {
                    'strategy_type': 'standard_stack',
                    'category': 'standard_stack',
                    'implied_odds_multiplier': 1.1,
                    'set_mining_threshold': 0.10,
                    'speculative_hands_bonus': 0.05,
                    'bet_sizing_preference': 0.70,
                    'bluff_frequency_bonus': 0.0,
                    'postflop_aggression': 1.0,
                    'drawing_hand_liberality': 1.0
                }
                
            elif effective_stack_bb > 40:  # Medium stack (40-80bb)
                strategy = {
                    'strategy_type': 'medium_stack',
                    'category': 'medium_stack',
                    'implied_odds_multiplier': 0.9,
                    'set_mining_threshold': 0.08,
                    'speculative_hands_bonus': 0.0,
                    'bet_sizing_preference': 0.75,
                    'bluff_frequency_bonus': -0.05,
                    'postflop_aggression': 1.05,  # More direct
                    'drawing_hand_liberality': 0.9
                }
                
            else:  # Short stack (<40bb)
                strategy = {
                    'strategy_type': 'short_stack',
                    'category': 'short_stack',
                    'implied_odds_multiplier': 0.7,
                    'set_mining_threshold': 0.05,
                    'speculative_hands_bonus': -0.1,
                    'bet_sizing_preference': 0.85,  # Larger, more commitment
                    'bluff_frequency_bonus': -0.1,
                    'postflop_aggression': 1.2,
                    'drawing_hand_liberality': 0.7
                }
            
            # SPR-specific adjustments
            if spr < 3:  # Low SPR - commitment oriented
                strategy['commitment_threshold'] = 0.3  # Commit easier
                strategy['protection_betting'] = 1.2
            elif spr > 8:  # High SPR - more cautious
                strategy['commitment_threshold'] = 0.5
                strategy['protection_betting'] = 0.9
            else:
                strategy['commitment_threshold'] = 0.4
                strategy['protection_betting'] = 1.0
                
            strategy['spr'] = spr
            strategy['effective_stack_bb'] = effective_stack_bb
            
            return strategy
        except Exception as e:
            logger.warning(f"Error in stack depth strategy: {e}")
            return {
                'strategy_type': 'standard_stack',
                'category': 'standard_stack',
                'implied_odds_multiplier': 1.0,
                'bet_sizing_preference': 0.70,
                'postflop_aggression': 1.0,
                'spr': 5.0
            }

    def analyze_thin_value_opportunity(self, hand_strength, win_probability, position,
                                     opponent_analysis, board_texture, street):
        """
        Analyze opportunities for thin value betting in cash games.
        
        Args:
            hand_strength: Hand strength classification  
            win_probability: Estimated win probability
            position: Player position
            opponent_analysis: Opponent tendencies and stats
            board_texture: Board texture analysis
            street: Current street
            
        Returns:
            dict: Thin value analysis and recommendations
        """
        try:
            position_adjustments = self.get_position_based_adjustments(
                position, street, hand_strength, 1, 100  # Default values
            )
            
            thin_value_threshold = position_adjustments['thin_value_threshold']
            
            # Adjust threshold based on opponent tendencies
            if opponent_analysis:
                avg_vpip = opponent_analysis.get('avg_vpip', 25)
                avg_calling_frequency = opponent_analysis.get('calling_frequency', 0.4)
                
                if avg_vpip > 30:  # Loose opponents
                    thin_value_threshold -= 0.05
                elif avg_vpip < 20:  # Tight opponents  
                    thin_value_threshold += 0.05
                    
                if avg_calling_frequency > 0.5:  # Call-happy opponents
                    thin_value_threshold -= 0.03
            
            # Board texture considerations
            if board_texture:
                if board_texture.get('draw_heavy', False):
                    thin_value_threshold += 0.03  # Need more equity vs draws
                if board_texture.get('dry', False):
                    thin_value_threshold -= 0.02  # Can bet thinner on dry boards
            
            # Street considerations
            if street == 'river':
                thin_value_threshold -= 0.02  # Can bet thinner on river
            elif street == 'flop':
                thin_value_threshold += 0.03  # Need more equity early
            
            is_thin_value = (
                hand_strength in ['medium', 'strong'] and
                win_probability >= thin_value_threshold and
                win_probability <= 0.70  # Not strong enough for pure value
            )
            
            # Sizing for thin value
            if is_thin_value:
                if street == 'river':
                    sizing_fraction = 0.55  # Smaller river thin value
                else:
                    sizing_fraction = 0.60  # Moderate sizing
            else:
                sizing_fraction = 0.0
            
            return {
                'is_thin_value': is_thin_value,
                'threshold_used': thin_value_threshold,
                'sizing_fraction': sizing_fraction,
                'confidence': min(1.0, (win_probability - thin_value_threshold) * 5),
                'reasoning': f'thin_value_{street}_pos_{position}_eq_{win_probability:.2f}'
            }
            
        except Exception as e:
            logger.warning(f"Error in thin value analysis: {e}")
            return {
                'is_thin_value': False,
                'threshold_used': 0.60,
                'sizing_fraction': 0.0,
                'confidence': 0.0,
                'reasoning': 'error_in_thin_value_analysis'
            }

    def get_river_decision_enhancement(self, hand_strength, win_probability, pot_odds,
                                     bet_to_call, pot_size, stack_size, position,
                                     opponent_analysis, board_texture):
        """
        Enhanced river decision making for cash games.
        
        Args:
            hand_strength: Hand strength classification
            win_probability: Estimated win probability
            pot_odds: Pot odds being offered
            bet_to_call: Amount to call
            pot_size: Current pot size
            stack_size: Our remaining stack
            position: Player position
            opponent_analysis: Opponent analysis data
            board_texture: Board texture information
            
        Returns:
            dict: Enhanced river decision analysis
        """
        try:
            # Base decision thresholds
            call_threshold = pot_odds * 1.05  # Need slight edge over pot odds
            
            # Position adjustments
            if position in ['BTN', 'CO']:  # Late position
                call_threshold *= 0.95  # Can call slightly wider
            elif position in ['SB', 'BB']:  # Blind positions
                call_threshold *= 1.05  # Need more equity
            
            # Opponent adjustments
            if opponent_analysis:
                bluff_frequency = opponent_analysis.get('river_bluff_frequency', 0.3)
                value_bet_frequency = opponent_analysis.get('value_bet_frequency', 0.7)
                
                # Against bluff-heavy opponents
                if bluff_frequency > 0.4:
                    call_threshold *= 0.9
                elif bluff_frequency < 0.2:
                    call_threshold *= 1.1
                
                # Against value-heavy opponents  
                if value_bet_frequency > 0.8:
                    call_threshold *= 1.05
            
            # Board texture considerations
            if board_texture:
                if board_texture.get('paired', False):
                    call_threshold *= 1.03  # Slightly more cautious on paired boards
                if board_texture.get('flush_possible', False):
                    call_threshold *= 1.02
                if board_texture.get('straight_possible', False):
                    call_threshold *= 1.02
            
            # Bet sizing tells
            bet_to_pot_ratio = bet_to_call / pot_size if pot_size > 0 else 1.0
            
            if bet_to_pot_ratio > 1.0:  # Overbet
                # Overpets are usually polarized (nuts or bluff)
                if hand_strength in ['weak_made', 'medium']:
                    call_threshold *= 1.15  # Much more cautious vs overbets
            elif bet_to_pot_ratio < 0.4:  # Small bet
                # Small bets often include more bluffs
                call_threshold *= 0.95
            
            # Stack size considerations
            stack_to_pot = stack_size / pot_size if pot_size > 0 else 10
            if stack_to_pot < 1.5:  # Short effective stack
                # When short, opponent more likely to bluff
                call_threshold *= 0.92
            
            # Final decision
            should_call = win_probability >= call_threshold
            
            # Calculate confidence in decision
            equity_surplus = win_probability - call_threshold
            confidence = min(1.0, abs(equity_surplus) * 3)
            
            return {
                'should_call': should_call,
                'call_threshold': call_threshold,
                'win_probability': win_probability,
                'equity_surplus': equity_surplus,
                'confidence': confidence,
                'bet_to_pot_ratio': bet_to_pot_ratio,
                'reasoning': f'river_call_{hand_strength}_pos_{position}_eq_{win_probability:.2f}_threshold_{call_threshold:.2f}'
            }
            
        except Exception as e:
            logger.warning(f"Error in river decision enhancement: {e}")
            return {
                'should_call': win_probability >= pot_odds,
                'call_threshold': pot_odds,
                'confidence': 0.5,
                'reasoning': 'fallback_river_decision'
            }

    def get_exploitative_adjustments(self, opponent_stats, table_dynamics, position, street):
        """
        Get exploitative adjustments based on opponent tendencies and table dynamics.
        
        Args:
            opponent_stats: Dictionary of opponent statistics
            table_dynamics: Table-wide tendencies and stats
            position: Our position
            street: Current street
            
        Returns:
            dict: Exploitative strategy adjustments
        """
        try:
            adjustments = {
                'value_sizing_multiplier': 1.0,
                'bluff_frequency_multiplier': 1.0,
                'calling_threshold_multiplier': 1.0,
                'aggression_multiplier': 1.0,
                'steal_frequency_multiplier': 1.0
            }
            
            if not opponent_stats:
                return adjustments
            
            # Analyze key opponent stats
            avg_vpip = opponent_stats.get('avg_vpip', 25)
            avg_pfr = opponent_stats.get('avg_pfr', 18)
            avg_aggression = opponent_stats.get('avg_aggression_factor', 2.0)
            fold_to_cbet = opponent_stats.get('fold_to_cbet', 0.6)
            
            # Against loose opponents (high VPIP)
            if avg_vpip > 35:
                adjustments['value_sizing_multiplier'] = 1.15  # Bet bigger for value
                adjustments['bluff_frequency_multiplier'] = 0.8  # Bluff less
                adjustments['calling_threshold_multiplier'] = 1.05  # Need more equity to call
            
            # Against tight opponents (low VPIP)  
            elif avg_vpip < 20:
                adjustments['value_sizing_multiplier'] = 0.9  # Smaller value bets
                adjustments['bluff_frequency_multiplier'] = 1.2  # Bluff more
                adjustments['steal_frequency_multiplier'] = 1.3  # Steal more
            
            # Against passive opponents (low aggression)
            if avg_aggression < 1.5:
                adjustments['value_sizing_multiplier'] = 1.1
                adjustments['bluff_frequency_multiplier'] = 1.15
                
            # Against aggressive opponents (high aggression)
            elif avg_aggression > 3.0:
                adjustments['calling_threshold_multiplier'] = 0.95  # Can call wider
                adjustments['bluff_frequency_multiplier'] = 0.85  # Bluff less
            
            # C-bet fold frequency adjustments
            if fold_to_cbet > 0.7:  # Opponents fold too much to c-bets
                adjustments['bluff_frequency_multiplier'] *= 1.2
            elif fold_to_cbet < 0.4:  # Opponents don't fold to c-bets
                adjustments['bluff_frequency_multiplier'] *= 0.8
                adjustments['value_sizing_multiplier'] *= 1.1
            
            # Table dynamics
            if table_dynamics:
                table_aggression = table_dynamics.get('average_aggression', 2.0)
                if table_aggression > 3.0:  # Aggressive table
                    adjustments['calling_threshold_multiplier'] *= 0.95
                elif table_aggression < 1.5:  # Passive table
                    adjustments['aggression_multiplier'] *= 1.1
            
            # Position-based exploitative adjustments
            if position in ['BTN', 'CO'] and street == 'flop':
                # More aggressive in position vs weak opponents
                if avg_vpip > 30 and avg_aggression < 2.0:
                    adjustments['aggression_multiplier'] *= 1.15
            
            return adjustments
            
        except Exception as e:
            logger.warning(f"Error in exploitative adjustments: {e}")
            return {
                'value_sizing_multiplier': 1.0,
                'bluff_frequency_multiplier': 1.0,
                'calling_threshold_multiplier': 1.0,
                'aggression_multiplier': 1.0,
                'steal_frequency_multiplier': 1.0
            }

    def get_bet_sizing_optimization(self, hand_strength, pot_size, street, position,
                                  opponent_count, stack_depth_bb, board_texture,
                                  opponent_stats=None):
        """
        Optimized bet sizing for cash games based on multiple factors.
        
        Args:
            hand_strength: Hand strength classification
            pot_size: Current pot size  
            street: Current street
            position: Player position
            opponent_count: Number of active opponents
            stack_depth_bb: Stack depth in big blinds
            board_texture: Board texture analysis
            opponent_stats: Opponent statistics
            
        Returns:
            dict: Optimized bet sizing recommendations
        """
        try:
            # Get base sizing from position adjustments
            position_adj = self.get_position_based_adjustments(
                position, street, hand_strength, opponent_count, stack_depth_bb
            )
            
            # Base sizing by hand strength and street
            base_sizing = {
                'very_strong': {'flop': 0.70, 'turn': 0.75, 'river': 0.80},
                'strong': {'flop': 0.65, 'turn': 0.70, 'river': 0.75},
                'medium': {'flop': 0.55, 'turn': 0.60, 'river': 0.65},
                'weak_made': {'flop': 0.40, 'turn': 0.45, 'river': 0.50},
                'drawing': {'flop': 0.45, 'turn': 0.50, 'river': 0.0}
            }
            
            base_fraction = base_sizing.get(hand_strength, {}).get(street, 0.60)
            
            # Apply position adjustments
            base_fraction *= position_adj['value_sizing_multiplier']
            
            # Stack depth adjustments
            stack_strategy = self.get_stack_depth_strategy(stack_depth_bb, stack_depth_bb, pot_size, 1)
            base_fraction *= (stack_strategy.get('bet_sizing_preference', 0.70) / 0.70)
            
            # Board texture adjustments
            if board_texture:
                if board_texture.get('wet', False) or board_texture.get('draw_heavy', False):
                    base_fraction *= 1.1  # Bet bigger for protection
                elif board_texture.get('dry', False):
                    base_fraction *= 0.95  # Can bet smaller on dry boards
                    
                if board_texture.get('paired', False):
                    base_fraction *= 0.95  # Slightly smaller on paired boards
            
            # Opponent count adjustments
            if opponent_count > 1:
                multiway_factor = max(0.7, 1.0 - (opponent_count - 1) * 0.15)
                base_fraction *= multiway_factor
            
            # Exploitative adjustments
            if opponent_stats:
                exploitative_adj = self.get_exploitative_adjustments(
                    opponent_stats, None, position, street
                )
                base_fraction *= exploitative_adj['value_sizing_multiplier']
            
            # Ensure reasonable bounds
            base_fraction = max(0.25, min(1.2, base_fraction))
            
            return {
                'sizing_fraction': base_fraction,
                'bet_amount': pot_size * base_fraction,
                'reasoning': f'optimized_{hand_strength}_{street}_pos_{position}_opps_{opponent_count}',
                'confidence': 0.8
            }
            
        except Exception as e:
            logger.warning(f"Error in bet sizing optimization: {e}")
            return {
                'sizing_fraction': 0.65,
                'bet_amount': pot_size * 0.65,
                'reasoning': 'fallback_sizing',
                'confidence': 0.5
            }

# Global instance for easy access
cash_game_enhancer = CashGameEnhancer()

def apply_cash_game_enhancements(decision_context):
    """
    Apply comprehensive cash game enhancements to a decision context.
    
    Args:
        decision_context: Dictionary containing all decision-making context
        
    Returns:
        dict: Enhanced decision recommendations
    """
    try:
        enhancer = cash_game_enhancer
        
        # Extract context
        position = decision_context.get('position', 'MP')
        street = decision_context.get('street', 'flop')
        hand_strength = decision_context.get('hand_strength', 'medium')
        win_probability = decision_context.get('win_probability', 0.5)
        pot_size = decision_context.get('pot_size', 1.0)
        stack_size = decision_context.get('stack_size', 100.0)
        big_blind = decision_context.get('big_blind', 1.0)
        active_opponents = decision_context.get('active_opponents_count', 1)
        opponent_analysis = decision_context.get('opponent_analysis', {})
        board_texture = decision_context.get('board_texture', {})
        
        stack_depth_bb = stack_size / big_blind if big_blind > 0 else 100
        
        # Get all enhancement components
        position_adj = enhancer.get_position_based_adjustments(
            position, street, hand_strength, active_opponents, stack_depth_bb
        )
        
        stack_strategy = enhancer.get_stack_depth_strategy(
            stack_depth_bb, stack_depth_bb, pot_size, big_blind
        )
        
        thin_value = enhancer.analyze_thin_value_opportunity(
            hand_strength, win_probability, position, opponent_analysis, board_texture, street
        )
        
        bet_sizing = enhancer.get_bet_sizing_optimization(
            hand_strength, pot_size, street, position, active_opponents,
            stack_depth_bb, board_texture, opponent_analysis
        )
        
        exploitative_adj = enhancer.get_exploitative_adjustments(
            opponent_analysis, None, position, street
        )
        
        # River-specific enhancements
        river_analysis = None
        if street == 'river':
            bet_to_call = decision_context.get('bet_to_call', 0)
            pot_odds = decision_context.get('pot_odds', 0.33)
            
            river_analysis = enhancer.get_river_decision_enhancement(
                hand_strength, win_probability, pot_odds, bet_to_call,
                pot_size, stack_size, position, opponent_analysis, board_texture
            )
        
        # Compile enhanced recommendations
        enhancements = {
            'position_adjustments': position_adj,
            'stack_strategy': stack_strategy,
            'thin_value_analysis': thin_value,
            'optimized_bet_sizing': bet_sizing,
            'exploitative_adjustments': exploitative_adj,
            'river_analysis': river_analysis,
            'overall_confidence': 0.85,
            'enhancement_version': '1.0'
        }
        
        logger.info(f"Cash game enhancements applied for {position} {street} {hand_strength}")
        return enhancements
        
    except Exception as e:
        logger.error(f"Error applying cash game enhancements: {e}")
        return {
            'position_adjustments': {'reasoning': 'error_fallback'},
            'stack_strategy': {'category': 'standard_stack'},
            'thin_value_analysis': {'is_thin_value': False},
            'optimized_bet_sizing': {'sizing_fraction': 0.65},
            'exploitative_adjustments': {},
            'river_analysis': None,
            'overall_confidence': 0.3,
            'enhancement_version': '1.0'
        }
