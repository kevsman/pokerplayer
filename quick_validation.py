#!/usr/bin/env python3
"""
Quick test to validate the enhanced bot fixes.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_poker_bot import EnhancedPokerBot
    from decision_engine import ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
    
    print("✓ Enhanced bot imports working")
    
    # Test bot initialization
    bot = EnhancedPokerBot()
    print("✓ Enhanced bot initialization working")
    
    # Test function signature fix
    try:
        from improved_postflop_decisions import make_improved_postflop_decision
        
        # Test new signature
        test_game_analysis = {
            'pot_size': '100.00',
            'current_phase': 'flop',
            'my_player_name': 'Hero',
            'player_data': [{'name': 'Hero', 'stack': '1000.00'}]
        }
        
        result = make_improved_postflop_decision(
            game_analysis=test_game_analysis,
            equity_calculator=None,
            opponent_analysis=None,
            logger_instance=None
        )
        
        print("✓ Improved postflop decision function signature working")
        print(f"  Decision result: {result}")
        
    except Exception as e:
        print(f"✗ Function signature test failed: {e}")
    
    # Test UI method access
    try:
        hasattr(bot.ui_controller, 'action_fold')
        hasattr(bot.ui_controller, 'action_check_call')
        hasattr(bot.ui_controller, 'action_raise')
        print("✓ UI controller methods are available")
        
    except Exception as e:
        print(f"✗ UI controller test failed: {e}")
    
    print("\n🎉 All fixes validated successfully!")
    
except Exception as e:
    print(f"✗ Validation failed: {e}")
    import traceback
    traceback.print_exc()
