#!/usr/bin/env python3
"""
Test that the safe strategy lookup still allows reasonable strategies through.
"""
import logging
from safe_strategy_lookup import SafeStrategyLookup

logging.basicConfig(level=logging.INFO)

def test_safe_strategies_allowed():
    """Test that the safe lookup doesn't reject all strategies."""
    
    lookup = SafeStrategyLookup()
    
    print("🔒 Testing Safe Strategy Lookup - Positive Cases")
    print("=" * 60)
    
    # Test with some random hashes to see if reasonable strategies get through
    test_hashes = [
        # Just test a few random strategies to see their aggression levels
        list(lookup.strategy_table.keys())[0],
        list(lookup.strategy_table.keys())[100], 
        list(lookup.strategy_table.keys())[1000],
        list(lookup.strategy_table.keys())[10000],
    ]
    
    safe_strategies_found = 0
    
    for i, test_hash in enumerate(test_hashes[:10]):  # Test first 10
        strategy = lookup.strategy_table[test_hash]
        
        # Calculate aggression
        total_aggression = sum(strategy.get(f'action_{i}', 0) for i in range(2, 6))
        
        # Test with strong hand context
        strong_context = {
            'stage': 'flop',
            'hand_strength': 'strong'
        }
        
        is_safe = lookup._is_strategy_safe_for_context(strategy, strong_context)
        
        print(f"Strategy {i+1}: aggression={total_aggression:.1%}, safe_for_strong_hand={is_safe}")
        
        if is_safe:
            safe_strategies_found += 1
    
    print(f"\nResult: {safe_strategies_found} out of {len(test_hashes)} strategies were deemed safe for strong hands")
    
    if safe_strategies_found > 0:
        print("✅ Good - the safe lookup is not overly restrictive")
    else:
        print("⚠️ Warning - the safe lookup might be too restrictive")

if __name__ == "__main__":
    test_safe_strategies_allowed()
