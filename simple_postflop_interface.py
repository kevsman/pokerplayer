# simple_postflop_interface.py

"""
Simplified interface for postflop decision making.
This wrapper provides a cleaner API for testing the enhanced postflop logic.
"""

import logging
from enhanced_postflop_decision_logic import make_enhanced_postflop_decision

logger = logging.getLogger(__name__)

def make_postflop_decision(
    numerical_hand_rank, 
    win_probability,
    pot_size,
    bet_to_call,
    my_stack,
    opponent_tracker=None,
    active_opponents_count=1,
    street="flop",
    position="button",
    actions_taken_this_street=None,
    pot_odds_to_call=0,
    aggression_factor=2.0,
    bluff_frequency=0.1
):
    """
    Simplified interface for postflop decisions.
    
    This function wraps the complex enhanced postflop decision logic
    with sensible defaults for testing purposes.
    """
    if actions_taken_this_street is None:
        actions_taken_this_street = []
    
    # Map parameters to what the enhanced function expects
    
    # Create mock decision engine with simple bluff function
    class MockDecisionEngine:
        def should_bluff_func(self, pot, stack, stage, win_prob):
            return win_prob < 0.3 and pot / stack > 0.3  # Simple bluff logic
    
    decision_engine_instance = MockDecisionEngine()
    
    # Derive hand description from numerical rank
    hand_descriptions = {
        1: "High Card",
        2: "One Pair", 
        3: "Two Pair",
        4: "Three of a Kind",
        5: "Straight",
        6: "Flush",
        7: "Full House", 
        8: "Four of a Kind",
        9: "Straight Flush"
    }
    hand_description = hand_descriptions.get(numerical_hand_rank, "Unknown")
    
    # Determine if we can check (no bet to call means we can check)
    can_check = (bet_to_call == 0)
    
    # Calculate SPR (Stack to Pot Ratio)
    spr = my_stack / pot_size if pot_size > 0 else 100
    
    # Action constants
    action_fold_const = "fold"
    action_check_const = "check"
    action_call_const = "call"
    action_raise_const = "raise"
    
    # Create mock player data
    my_player_data = {
        'position': position,
        'current_bet': 0,
        'hand': ["XX", "XX"],  # Mock hand cards
        'community_cards': ["XX", "XX", "XX"],  # Mock community cards
        'is_all_in_call_available': False
    }
    
    # Estimate big blind (rough estimate based on pot size)
    big_blind_amount = max(0.02, pot_size * 0.1)  # Conservative estimate
    
    # Calculate max bet on table
    max_bet_on_table = bet_to_call
    
    try:
        # Call the enhanced postflop decision function
        decision, amount = make_enhanced_postflop_decision(
            decision_engine_instance=decision_engine_instance,
            numerical_hand_rank=numerical_hand_rank,
            hand_description=hand_description,
            bet_to_call=bet_to_call,
            can_check=can_check,
            pot_size=pot_size,
            my_stack=my_stack,
            win_probability=win_probability,
            pot_odds_to_call=pot_odds_to_call,
            game_stage=street,  # The enhanced function expects 'game_stage'
            spr=spr,
            action_fold_const=action_fold_const,
            action_check_const=action_check_const,
            action_call_const=action_call_const,
            action_raise_const=action_raise_const,
            my_player_data=my_player_data,
            big_blind_amount=big_blind_amount,
            base_aggression_factor=aggression_factor,
            max_bet_on_table=max_bet_on_table,
            active_opponents_count=active_opponents_count,
            opponent_tracker=opponent_tracker
        )
        
        logger.info(f"Simplified interface decision: {decision}, amount: {amount}")
        return decision, amount
        
    except Exception as e:
        logger.error(f"Error in simplified postflop interface: {e}")
        # Fallback to basic logic
        if bet_to_call == 0:
            return action_check_const, 0
        elif win_probability > pot_odds_to_call:
            return action_call_const, bet_to_call
        else:
            return action_fold_const, 0
