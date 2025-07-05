"""
Monte Carlo solver module for PokerBotV2.
Implements fast Monte Carlo simulation with heuristic opponent modeling for real-time poker decisions.
This is NOT a CFR solver - it's a fast heuristic approach for fallback situations.
"""
import random
import logging
import time
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator
from hand_abstraction import HandAbstraction

logger = logging.getLogger(__name__)

class MonteCarloSolver:
    def __init__(self, abstraction: 'HandAbstraction', hand_evaluator: HandEvaluator, equity_calculator: EquityCalculator, logger_instance=None):
        self.abstraction = abstraction
        self.hand_evaluator = hand_evaluator
        self.equity_calculator = equity_calculator
        self.logger = logger_instance if logger_instance else logger

    def solve(self, player_hole_cards, community_cards, pot_size, actions, stage, num_opponents=2, iterations=25, max_time_seconds=1.5):
        """
        Improved Monte Carlo simulation with better heuristic opponent modeling.
        
        This solver uses Monte Carlo simulation to estimate action values based on:
        1. Hand equity calculations
        2. Improved opponent response modeling based on hand strength
        3. Proper fold baseline modeling
        4. Better strategy normalization
        
        This is optimized for speed (~2 seconds) with improved decision quality.
        """
        start_time = time.time()
        action_scores = {action: 0.0 for action in actions}
        
        # Calculate hand equity once for efficiency
        win_prob, tie_prob, lose_prob = self.equity_calculator.calculate_equity_monte_carlo(
            [player_hole_cards], community_cards, None, 
            num_simulations=50, num_opponents=num_opponents
        )
        
        # EMERGENCY FIX: Detect broken equity calculation and use fallback
        total_prob = win_prob + tie_prob + lose_prob  # Check if probabilities sum properly
        if total_prob < 0.8 or total_prob > 1.2 or win_prob < 0:
            self.logger.warning(f"🚨 Detected broken equity calculation (total={total_prob:.3f}, win={win_prob:.3f}). Using fallback hand strength.")
            win_prob = self._simple_hand_strength_estimate(player_hole_cards, community_cards, stage)
            self.logger.info(f"🔧 Fallback hand strength: {win_prob:.3f}")
        
        # Hand strength categories for better decision making  
        # Adjust thresholds based on stage (river is more decisive)
        if stage == "preflop":
            # Preflop: Different thresholds since equity is multi-way potential
            # More aggressive trash classification for bad preflop hands
            if win_prob >= 0.85:
                hand_strength = "nuts"    # AA, KK
            elif win_prob >= 0.65:
                hand_strength = "strong"  # QQ, JJ, TT, 99, AK
            elif win_prob >= 0.45:
                hand_strength = "medium"  # 88, 77, AQ, AJ, KQ
            elif win_prob >= 0.35:
                hand_strength = "weak"    # Small pairs, suited connectors
            else:
                hand_strength = "trash"   # 72o, etc. (anything below 35%)
        elif stage == "river":
            # River: More conservative thresholds since hand is final
            if win_prob >= 0.90:
                hand_strength = "nuts"
            elif win_prob >= 0.75:
                hand_strength = "strong"
            elif win_prob >= 0.55:
                hand_strength = "medium"
            elif win_prob >= 0.25:
                hand_strength = "weak"
            else:
                hand_strength = "trash"
        else:
            # Flop/Turn: Standard thresholds
            if win_prob >= 0.85:
                hand_strength = "nuts"
            elif win_prob >= 0.70:
                hand_strength = "strong"
            elif win_prob >= 0.45:
                hand_strength = "medium"
            elif win_prob >= 0.20:
                hand_strength = "weak"
            else:
                hand_strength = "trash"
            
        self.logger.debug(f"Hand equity: {win_prob:.3f} ({hand_strength})")

        for iteration in range(iterations):
            # Check time limit every 10 iterations
            if iteration % 10 == 0 and time.time() - start_time > max_time_seconds:
                self.logger.debug(f"Monte Carlo solver hit time limit of {max_time_seconds}s after {iteration} iterations")
                break

            # Model each action's expected value
            
            # FOLD: Always has EV of 0 (baseline)
            if 'fold' in actions:
                action_scores['fold'] += 0.0
            
            # CALL/CHECK: Win probability * pot size (no additional investment for check)
            if 'call' in actions:
                call_cost = pot_size * 0.1  # Assume we need to call some amount
                if hand_strength == "trash":
                    # Trash hands should rarely call - heavy penalty
                    action_scores['call'] += (win_prob * pot_size - call_cost) * 0.1
                else:
                    action_scores['call'] += win_prob * pot_size - call_cost
                
            if 'check' in actions:
                action_scores['check'] += win_prob * pot_size  # No cost to check
            
            # RAISE/BET: More complex modeling based on hand strength and opponent response
            if 'raise' in actions:
                # Use more deterministic opponent modeling based on hand strength
                if stage == 'river' and hand_strength in ['weak', 'trash']:
                    # River bluffs with weak hands should be extremely rare
                    fold_prob = 0.97  # Very high fold equity needed
                    bet_size = pot_size * 1.0
                    # Expected value calculation with heavy penalty for river bluffs
                    ev_if_fold = pot_size * 0.05  # Very low reward even if they fold
                    ev_if_call = -bet_size * 3.0  # Heavy penalty if called
                    action_scores['raise'] += fold_prob * ev_if_fold + (1 - fold_prob) * ev_if_call
                elif hand_strength == "nuts":
                    # Very strong hands: opponents fold less, we want action
                    fold_prob = 0.4  # 40% fold
                    bet_size = pot_size * 0.75
                    total_pot = pot_size + (2 * bet_size)
                    ev_if_fold = pot_size
                    ev_if_call = win_prob * total_pot - bet_size
                    action_scores['raise'] += fold_prob * ev_if_fold + (1 - fold_prob) * ev_if_call
                elif hand_strength == "strong":
                    # Strong hands: decent fold equity
                    fold_prob = 0.65  # 65% fold
                    bet_size = pot_size * 0.75
                    total_pot = pot_size + (2 * bet_size)
                    ev_if_fold = pot_size
                    ev_if_call = win_prob * 0.8 * total_pot - bet_size  # Calling range stronger
                    action_scores['raise'] += fold_prob * ev_if_fold + (1 - fold_prob) * ev_if_call
                elif hand_strength == "medium":
                    # Medium hands: some fold equity, but risky
                    fold_prob = 0.55  # 55% fold
                    bet_size = pot_size * 0.75
                    total_pot = pot_size + (2 * bet_size)
                    ev_if_fold = pot_size
                    ev_if_call = win_prob * 0.7 * total_pot - bet_size
                    action_scores['raise'] += fold_prob * ev_if_fold + (1 - fold_prob) * ev_if_call
                elif hand_strength == "weak":
                    # Weak hands: good fold equity needed for bluffs
                    fold_prob = 0.75  # 75% fold
                    bet_size = pot_size * 0.75
                    total_pot = pot_size + (2 * bet_size)
                    ev_if_fold = pot_size * 0.6  # Lower bluff reward
                    ev_if_call = win_prob * 0.6 * total_pot - bet_size
                    action_scores['raise'] += fold_prob * ev_if_fold + (1 - fold_prob) * ev_if_call
                else:  # trash
                    # Trash hands: need very high fold equity, rarely profitable
                    fold_prob = 0.85  # 85% fold needed
                    bet_size = pot_size * 0.75
                    ev_if_fold = pot_size * 0.3  # Low bluff reward
                    ev_if_call = -bet_size * 2.0  # Heavy penalty
                    action_scores['raise'] += fold_prob * ev_if_fold + (1 - fold_prob) * ev_if_call
            
            if 'bet' in actions:
                # Similar to raise logic
                action_scores['bet'] = action_scores.get('raise', 0)

        # Convert scores to probabilities using softmax-like approach
        # This ensures better normalization and more realistic strategies
        
        # First, normalize scores to positive values
        min_score = min(action_scores.values()) if action_scores.values() else 0
        if min_score < 0:
            action_scores = {action: score - min_score + 0.1 for action, score in action_scores.items()}
        
        # Apply hand-strength-based strategy adjustments
        strategy = self._apply_hand_strength_adjustments(action_scores, hand_strength, actions, stage)
        
        # Ensure probabilities sum to 1.0
        total_prob = sum(strategy.values())
        if total_prob > 0:
            strategy = {action: prob / total_prob for action, prob in strategy.items()}
        else:
            # Fallback: heavily favor folding/checking over aggressive actions
            if 'fold' in actions:
                strategy = {'fold': 0.9}
                remaining_prob = 0.1
                other_actions = [a for a in actions if a != 'fold']
                if other_actions:
                    prob_per_other = remaining_prob / len(other_actions)
                    for action in other_actions:
                        strategy[action] = prob_per_other
            elif 'check' in actions:
                strategy = {'check': 0.9}
                remaining_prob = 0.1
                other_actions = [a for a in actions if a != 'check']
                if other_actions:
                    prob_per_other = remaining_prob / len(other_actions)
                    for action in other_actions:
                        strategy[action] = prob_per_other
            else:
                # True fallback: equal probability for all actions
                strategy = {action: 1.0 / len(actions) for action in actions}
        
        self.logger.debug(f"Monte Carlo Solver calculated strategy: {strategy}")
        return strategy
    
    def _apply_hand_strength_adjustments(self, action_scores, hand_strength, actions, stage):
        """Apply hand-strength-based adjustments to create more realistic strategies."""
        strategy = {}
        
        # Convert scores to probabilities with hand-strength bias
        for action in actions:
            score = action_scores.get(action, 0.1)
            
            # Apply hand strength multipliers with more aggressive fold modeling
            if action == 'fold':
                # Base fold score should be significant for bad hands
                base_fold_score = 1.0
                if hand_strength == "trash":
                    score = base_fold_score * 50.0  # Very high fold tendency
                elif hand_strength == "weak":
                    score = base_fold_score * 20.0  # High fold tendency
                elif hand_strength == "medium":
                    score = base_fold_score * 5.0   # Moderate fold tendency
                elif hand_strength == "strong":
                    score = base_fold_score * 0.2   # Low fold tendency
                else:  # nuts
                    score = base_fold_score * 0.05  # Very low fold tendency
                    
            elif action in ['raise', 'bet']:
                # Special river considerations for betting/raising
                if stage == 'river' and hand_strength in ['weak', 'trash']:
                    score *= 0.01  # Extremely rare river bluffs with weak hands
                elif hand_strength == "nuts":
                    score *= 15.0  # Very likely to raise nuts
                elif hand_strength == "strong":
                    score *= 8.0   # Often raise strong hands
                elif hand_strength == "medium":
                    score *= 2.5   # Sometimes raise medium hands
                elif hand_strength == "weak":
                    score *= 0.5   # Rarely raise weak hands
                else:  # trash
                    score *= 0.05  # Almost never raise trash
                    
            elif action in ['call', 'check']:
                if hand_strength == "trash":
                    # Trash hands should strongly prefer passive actions
                    score *= 100.0  # Very high tendency to check/call
                elif hand_strength == "weak":
                    score *= 20.0   # High tendency to check/call
                elif hand_strength == "medium":
                    score *= 5.0    # Medium hands often call/check
                elif hand_strength == "strong":
                    score *= 3.0    # Strong hands sometimes call/check
                else:  # nuts
                    score *= 1.0    # Default for nuts
            
            strategy[action] = max(score, 0.001)  # Lower minimum to preserve ratios
        
        return strategy

    def _simple_hand_strength_estimate(self, hole_cards, community_cards, stage):
        """
        Simple hand strength estimate without complex equity calculations.
        This is a fallback for when the main equity calculator is broken.
        """
        if not hole_cards or len(hole_cards) != 2:
            return 0.3
        
        # Extract ranks and suits
        def parse_card(card):
            if len(card) >= 2:
                if card.startswith('10'):
                    return '10', card[-1]
                else:
                    return card[:-1], card[-1]
            return card[0], card[1] if len(card) > 1 else ''
        
        rank1, suit1 = parse_card(hole_cards[0])
        rank2, suit2 = parse_card(hole_cards[1])
        
        # Normalize ranks
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                       '9': 9, '10': 10, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        val1 = rank_values.get(rank1, 2)
        val2 = rank_values.get(rank2, 2)
        
        # Pocket pairs
        if val1 == val2:
            if val1 >= 13:  # AA, KK
                return 0.85 if stage == 'preflop' else 0.75
            elif val1 >= 11:  # QQ, JJ  
                return 0.80 if stage == 'preflop' else 0.70
            elif val1 >= 8:   # TT, 99, 88
                return 0.70 if stage == 'preflop' else 0.60
            else:
                return 0.55 if stage == 'preflop' else 0.45
        
        # High cards
        max_val = max(val1, val2)
        min_val = min(val1, val2)
        
        if max_val == 14:  # Ace
            if min_val >= 13:  # AK
                return 0.70 if stage == 'preflop' else 0.55
            elif min_val >= 11:  # AQ, AJ
                return 0.65 if stage == 'preflop' else 0.50
            elif min_val >= 9:   # AT, A9
                return 0.55 if stage == 'preflop' else 0.45
            else:  # Weak ace
                return 0.45 if stage == 'preflop' else 0.35
        
        if max_val >= 13:  # King high
            if min_val >= 12:  # KQ
                return 0.60 if stage == 'preflop' else 0.45
            elif min_val >= 10:  # KJ, KT
                return 0.55 if stage == 'preflop' else 0.40
            else:
                return 0.45 if stage == 'preflop' else 0.30
        
        # Lower cards
        if max_val >= 11:  # Queen, Jack high
            return 0.45 if stage == 'preflop' else 0.30
        else:
            return 0.30 if stage == 'preflop' else 0.20
