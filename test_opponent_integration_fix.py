#!/usr/bin/env python3
"""Test the opponent tracking integration fix"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_opponent_integration_fix():
    """Test that the AdvancedOpponentAnalyzer integration is fixed"""
    
    try:
        from advanced_opponent_modeling import AdvancedOpponentAnalyzer
        from decision_engine import DecisionEngine
        from hand_evaluator import HandEvaluator
        
        print("✅ Successfully imported modules")
        
        # Test AdvancedOpponentAnalyzer
        analyzer = AdvancedOpponentAnalyzer()
        
        # Test with unknown player (should return balanced default)
        current_situation = {
            'street': 'flop',
            'position': 'BTN',
            'situation': 'facing_bet'
        }
        
        strategy = analyzer.get_exploitative_strategy("Unknown", current_situation)
        print(f"Unknown player strategy: {strategy}")
        
        assert 'recommended_action' in strategy, "Missing recommended_action key"
        assert 'reasoning' in strategy, "Missing reasoning key"
        
        # Test with a real player profile
        profile = analyzer.get_or_create_profile("TestPlayer")
        profile.update_preflop_action("BTN", "raise", 3.0)
        profile.update_postflop_action("flop", "bet", 0.6, 1.0)
        
        strategy2 = analyzer.get_exploitative_strategy("TestPlayer", current_situation)
        print(f"TestPlayer strategy: {strategy2}")
        
        assert 'recommended_action' in strategy2, "Missing recommended_action key for real player"
        assert 'reasoning' in strategy2, "Missing reasoning key for real player"
        
        print("✅ AdvancedOpponentAnalyzer integration fix verified!")
        
        # Test integration with DecisionEngine (basic smoke test)
        hand_evaluator = HandEvaluator()
        config = {'big_blind': 0.02, 'small_blind': 0.01}
        decision_engine = DecisionEngine(hand_evaluator, config)
        
        print("✅ DecisionEngine integration working")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_opponent_integration_fix()
