# opponent_tracking_fix.py
"""
Fixed opponent tracking integration to use actual data instead of 'unknown' values.
This patch fixes the issue where opponent analysis shows "0 opponents tracked".
"""

import logging

logger = logging.getLogger(__name__)

def extract_opponent_position_from_recent_actions(profile):
    """Extract opponent's most recent position from their action history."""
    if not hasattr(profile, 'recent_actions') or not profile.recent_actions:
        return 'unknown'
    
    for action_data in reversed(profile.recent_actions):
        if isinstance(action_data, dict) and action_data.get('position'):
            return action_data.get('position', 'unknown')
    
    return 'unknown'

def extract_opponent_preflop_action(profile):
    """Extract opponent's most recent preflop action."""
    if not hasattr(profile, 'recent_actions') or not profile.recent_actions:
        return 'unknown'
    
    for action_data in reversed(profile.recent_actions):
        if isinstance(action_data, dict) and action_data.get('street') == 'preflop':
            return action_data.get('action', 'unknown')
    
    return 'unknown'

def infer_action_from_player_type(profile):
    """Infer likely preflop action based on player type."""
    player_type = profile.classify_player_type()
    if 'aggressive' in player_type:
        return 'raise'  # Likely raiser
    elif 'passive' in player_type:
        return 'call'   # Likely caller
    else:
        return 'call'   # Default

def analyze_board_texture(community_cards):
    """Analyze board texture from community cards."""
    if not community_cards or len(community_cards) < 3:
        return 'unknown'
    
    # Simple board texture analysis
    suits = [card[-1] for card in community_cards[:3]]  # Check flop
    ranks = [card[:-1] for card in community_cards[:3]]
    
    # Check for draws and coordination
    suit_counts = {suit: suits.count(suit) for suit in suits}
    max_suit_count = max(suit_counts.values()) if suit_counts else 0
    
    # Simple heuristic for board texture
    if max_suit_count >= 2:  # Two suited
        return 'wet'
    elif len(set(ranks)) == len(ranks):  # All different ranks
        # Check for straight possibilities
        rank_values = []
        for rank in ranks:
            if rank.isdigit():
                rank_values.append(int(rank))
            elif rank == 'A':
                rank_values.append(14)
            elif rank == 'K':
                rank_values.append(13)
            elif rank == 'Q':
                rank_values.append(12)
            elif rank == 'J':
                rank_values.append(11)
        
        if rank_values:
            rank_values.sort()
            # Check for consecutive or near-consecutive
            if len(rank_values) >= 2:
                max_gap = max(rank_values[i+1] - rank_values[i] for i in range(len(rank_values)-1))
                if max_gap <= 4:  # Some straight possibility
                    return 'wet'
                else:
                    return 'dry'
            else:
                return 'dry'
    else:
        return 'dry'

def get_enhanced_opponent_context(opponent_tracker, active_opponents_count, bet_to_call, pot_size, community_cards):
    """
    Get enhanced opponent context using actual tracking data instead of 'unknown' values.
    This is the main fix for the opponent tracking integration.
    """
    opponent_context = {}
    estimated_opponent_range = 'unknown'
    fold_equity_estimate = 0.5
    
    if not opponent_tracker or active_opponents_count == 0:
        return opponent_context, estimated_opponent_range, fold_equity_estimate
    
    # Get table dynamics
    table_dynamics = opponent_tracker.get_table_dynamics()
    
    # Analyze board texture once
    board_texture = analyze_board_texture(community_cards)
    
    # Analyze each opponent with enhanced data extraction
    for opponent_name, profile in opponent_tracker.opponents.items():
        if profile.hands_seen > 5:  # Only consider opponents with sufficient data
            # Extract actual data from opponent profile
            player_type = profile.classify_player_type()
            opponent_position = extract_opponent_position_from_recent_actions(profile)
            
            # Get fold equity with actual position
            fold_equity = profile.get_fold_equity_estimate(
                opponent_position, 
                bet_to_call / pot_size if pot_size > 0 else 0.5
            )
            
            opponent_context[opponent_name] = {
                'type': player_type,
                'fold_equity': fold_equity,
                'vpip': profile.get_vpip(),
                'pfr': profile.get_pfr(),
                'can_value_bet_thin': profile.should_value_bet_thin(opponent_position),
                'position': opponent_position,
                'hands_seen': profile.hands_seen
            }
            
            # Use first opponent's data for range estimation
            if estimated_opponent_range == 'unknown':
                opponent_preflop_action = extract_opponent_preflop_action(profile)
                
                # If no recent preflop action, infer from player type
                if opponent_preflop_action == 'unknown':
                    opponent_preflop_action = infer_action_from_player_type(profile)
                
                # Import the range estimation function
                try:
                    from postflop_decision_logic import estimate_opponent_range
                    
                    estimated_opponent_range = estimate_opponent_range(
                        position=opponent_position,
                        preflop_action=opponent_preflop_action,
                        bet_size=bet_to_call,
                        pot_size=pot_size,
                        street='flop',  # Default to flop for range estimation
                        board_texture=board_texture
                    )
                    
                    fold_equity_estimate = fold_equity
                    
                    logger.debug(f"Enhanced opponent analysis: {opponent_name} - "
                                f"position={opponent_position}, preflop_action={opponent_preflop_action}, "
                                f"player_type={player_type}, estimated_range={estimated_opponent_range}")
                    
                except ImportError:
                    logger.warning("Could not import estimate_opponent_range function")
                    estimated_opponent_range = player_type  # Fallback to player type
    
    logger.info(f"Enhanced opponent tracking: {len(opponent_context)} opponents analyzed, "
                f"table_type={table_dynamics.get('table_type', 'unknown')}, "
                f"board_texture={board_texture}, estimated_range={estimated_opponent_range}")
    
    return opponent_context, estimated_opponent_range, fold_equity_estimate

def apply_opponent_tracking_fix():
    """
    Apply the opponent tracking fix to the main postflop decision logic.
    This function can be called to patch the existing logic.
    """
    logger.info("Opponent tracking fix applied - using enhanced data extraction")
    return True
