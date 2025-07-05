#!/usr/bin/env python3
"""
Test the safe strategy lookup to ensure it rejects dangerous fuzzy matches.
"""
import logging
from safe_strategy_lookup import SafeStrategyLookup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_safe_strategy_lookup():
    """Test the safe strategy lookup with the problematic scenario."""
    
    # Initialize the safe lookup
    lookup = SafeStrategyLookup()
    
    print("🔒 Testing Safe Strategy Lookup")
    print("=" * 60)
    
    # Test the exact scenario that caused the problem
    target_hash = 4929814766040804927  # The bot's hash that matched aggressively
    problematic_match_hash = 7848782567973857233  # The aggressive strategy that was matched
    
    # Check if the problematic strategy exists
    problematic_strategy = lookup.get_strategy_by_hash(problematic_match_hash)
    if problematic_strategy:
        print(f"Found problematic strategy: {problematic_strategy}")
        
        # Calculate aggression level
        total_aggression = sum(problematic_strategy.get(f'action_{i}', 0) for i in range(2, 6))
        print(f"Total aggression level: {total_aggression:.1%}")
        
        # Test context-based safety check
        river_weak_context = {
            'stage': 'river',
            'hand_strength': 'weak'
        }
        
        is_safe = lookup._is_strategy_safe_for_context(problematic_strategy, river_weak_context)
        print(f"Safe for river weak hand: {is_safe}")
    
    # Test the safe lookup for the original hash
    state_components = {
        'street': 3,  # River
        'turn_index': 4,
        'max_bet': 0.58,
        'effective_pot': 1.94,
        'num_active': 6,
        'avg_bet': 0.1
    }
    
    hole_cards = ['3♥', '10♥']  # Weak hand
    community_cards = ['Q♦', '7♥', 'A♣', 'A♦', '9♣']  # Paired board
    
    strategy, match_type = lookup.get_strategy_with_conservative_fallback(
        target_hash, state_components, hole_cards, community_cards
    )
    
    print(f"\nResult for target hash {target_hash}:")
    print(f"Strategy found: {strategy is not None}")
    print(f"Match type: {match_type}")
    
    if strategy:
        total_aggression = sum(strategy.get(f'action_{i}', 0) for i in range(2, 6))
        print(f"Strategy aggression: {total_aggression:.1%}")
    else:
        print("✅ No unsafe strategy matched - will use Monte Carlo fallback")

if __name__ == "__main__":
    test_safe_strategy_lookup()
