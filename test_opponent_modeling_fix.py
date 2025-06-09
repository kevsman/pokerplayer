#!/usr/bin/env python3
"""
Test to verify the advanced opponent modeling fix.
This should resolve the "insufficient_opponent_data" issue.
"""

import sys
sys.path.append('.')

def test_advanced_opponent_fix():
    """Test that the advanced opponent modeling now works with opponent tracker data."""
    print("=== Testing Advanced Opponent Modeling Fix ===\n")
    
    try:
        # Import necessary modules
        from advanced_opponent_modeling import AdvancedOpponentAnalyzer
        from opponent_tracking import OpponentTracker
        
        print("✓ Modules imported successfully")
        
        # Create opponent tracker and add some test data
        tracker = OpponentTracker()
        tracker.update_opponent_action("TestPlayer1", "raise", "preflop", "BTN", 6.0, 2.0)
        tracker.update_opponent_action("TestPlayer1", "bet", "flop", "BTN", 4.5, 8.5)
        tracker.update_opponent_action("TestPlayer1", "call", "turn", "BTN", 3.0, 16.5)
        
        print(f"✓ Created opponent tracker with {len(tracker.opponents)} opponents")
        
        # Get opponent profile from tracker
        if "TestPlayer1" in tracker.opponents:
            profile = tracker.opponents["TestPlayer1"]
            print(f"  TestPlayer1: {profile.hands_seen} hands, VPIP={profile.get_vpip():.1f}%, PFR={profile.get_pfr():.1f}%")
        
        # Create advanced analyzer
        analyzer = AdvancedOpponentAnalyzer()
        print("✓ Created advanced analyzer")
        
        # Test the update_opponent_profile method that was missing
        for opponent_name, profile in tracker.opponents.items():
            if profile.hands_seen > 0:
                analyzer.update_opponent_profile(opponent_name, {
                    'vpip': profile.get_vpip(),
                    'pfr': profile.get_pfr(),
                    'hands_seen': profile.hands_seen
                })
        
        print(f"✓ Updated opponent profiles: {len(analyzer.profiles)} profiles created")
        
        # Test exploitative strategy (should no longer return "insufficient_opponent_data")
        current_situation = {
            'street': 'flop',
            'position': 'BTN',
            'situation': 'checked_to'
        }
        
        strategy = analyzer.get_exploitative_strategy("TestPlayer1", current_situation)
        
        print(f"✓ Exploitative strategy generated:")
        print(f"  Action: {strategy['recommended_action']}")
        print(f"  Reasoning: {strategy['reasoning']}")
        print(f"  Sizing: {strategy['sizing_adjustment']}")
        
        # Check if we still get "insufficient_opponent_data"
        if strategy['reasoning'] == 'insufficient_opponent_data':
            print("✗ STILL GETTING insufficient_opponent_data - fix didn't work!")
            return False
        else:
            print("✓ SUCCESS: No longer getting 'insufficient_opponent_data'!")
            return True
            
    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_advanced_opponent_fix()
    if success:
        print("\n🎉 Fix verification PASSED! The advanced opponent modeling should now work properly.")
    else:
        print("\n❌ Fix verification FAILED! Additional work may be needed.")
