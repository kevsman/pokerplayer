#!/usr/bin/env python3
"""
Improved comprehensive test script for the enhanced poker bot decision engine.
Tests various scenarios with proper betting situations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from html_parser import PokerPageParser
from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_improved_scenarios():
    """Test decision engine with properly structured betting scenarios"""
    print("=" * 60)
    print("IMPROVED COMPREHENSIVE POKER BOT TESTING")
    print("=" * 60)
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)
    
    # Scenario 1: Pocket Aces Preflop - facing a raise
    print("\nScenario 1: Pocket Aces Preflop - Facing Raise")
    print("-" * 50)
    
    my_player_1 = {
        'hole_cards': ['As', 'Ah'],
        'cards': ['As', 'Ah'],
        'stack': '14.96',
        'bet': '0.02',  # We've posted big blind
        'chips': 14.96,
        'current_bet': 0.02,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (2, "Pair of Aces", [14, 14])
    }
    
    table_data_1 = {
        'community_cards': [],
        'pot_size': '0.13',  # SB + BB + raise
        'current_bet_level': 0.08,
        'game_stage': 'Preflop'
    }
    
    all_players_1 = [
        my_player_1,
        {'chips': 10.0, 'current_bet': 0.08, 'is_active': True, 'bet': '0.08'},  # Raiser
        {'chips': 8.5, 'current_bet': 0.01, 'is_active': True, 'bet': '0.01'}   # Small blind
    ]
    
    try:
        decision1 = decision_engine.make_decision(my_player_1, table_data_1, all_players_1)
        print(f"Decision with pocket aces vs raise: {decision1}")
        print("Expected: Should 3-bet aggressively")
        
    except Exception as e:
        print(f"Error in scenario 1: {e}")
        import traceback
        traceback.print_exc()
    
    # Scenario 2: Weak hand (7-2 offsuit) facing large bet on flop
    print("\nScenario 2: Weak Hand (7-2) Facing Large Bet on Flop")
    print("-" * 50)
    
    my_player_2 = {
        'hole_cards': ['7s', '2h'],
        'cards': ['7s', '2h'],
        'stack': '10.00',
        'bet': '0.50',  # We've made a small bet
        'chips': 10.00,
        'current_bet': 0.50,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "High Card", [7, 2])
    }
    
    table_data_2 = {
        'community_cards': ['Kd', 'Qc', 'Js'],
        'pot_size': '7.50',  # Previous betting + our bet + opponent's large bet
        'current_bet_level': 5.00,
        'game_stage': 'Flop'
    }
    
    all_players_2 = [
        my_player_2,
        {'chips': 15.0, 'current_bet': 5.00, 'is_active': True, 'bet': '5.00'}  # Large bet from opponent
    ]
    
    try:
        decision2 = decision_engine.make_decision(my_player_2, table_data_2, all_players_2)
        print(f"Decision with 7-2 vs large bet: {decision2}")
        print("Expected: Should fold (terrible hand vs large bet)")
        
    except Exception as e:
        print(f"Error in scenario 2: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 3: Full House on River - facing moderate bet
    print("\nScenario 3: Full House on River - Facing Moderate Bet")
    print("-" * 50)
    
    my_player_3 = {
        'hole_cards': ['Ah', 'Kd'],
        'cards': ['Ah', 'Kd'],
        'stack': '20.00',
        'bet': '1.00',  # We've made a small bet
        'chips': 20.00,
        'current_bet': 1.00,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (7, "Full House", [14, 13])
    }
    
    table_data_3 = {
        'community_cards': ['As', 'Kc', 'Kh', 'Qh', 'Ad'],
        'pot_size': '18.00',
        'current_bet_level': 4.00,
        'game_stage': 'River'
    }
    
    all_players_3 = [
        my_player_3,
        {'chips': 25.0, 'current_bet': 4.00, 'is_active': True, 'bet': '4.00'}  # Moderate bet
    ]
    
    try:
        decision3 = decision_engine.make_decision(my_player_3, table_data_3, all_players_3)
        print(f"Decision with Full House vs moderate bet: {decision3}")
        print("Expected: Should raise/reraise for value")
        
    except Exception as e:
        print(f"Error in scenario 3: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 4: Flush Draw on Turn - facing reasonable bet
    print("\nScenario 4: Flush Draw on Turn - Facing Reasonable Bet")
    print("-" * 50)
    
    my_player_4 = {
        'hole_cards': ['Ah', 'Kh'],
        'cards': ['Ah', 'Kh'],
        'stack': '15.00',
        'bet': '0.50',  # Small bet from us
        'chips': 15.00,
        'current_bet': 0.50,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "Ace High", [14, 13])  # Strong draw but still high card
    }
    
    table_data_4 = {
        'community_cards': ['Qh', '7h', '2s', 'Jd'],  # Strong flush draw
        'pot_size': '6.00',
        'current_bet_level': 2.00,
        'game_stage': 'Turn'
    }
    
    all_players_4 = [
        my_player_4,
        {'chips': 20.0, 'current_bet': 2.00, 'is_active': True, 'bet': '2.00'}  # Reasonable bet
    ]
    
    try:
        decision4 = decision_engine.make_decision(my_player_4, table_data_4, all_players_4)
        print(f"Decision with flush draw vs reasonable bet: {decision4}")
        print("Expected: Should call (good pot odds for strong draw)")
        
    except Exception as e:
        print(f"Error in scenario 4: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 5: Top Pair on Flop - facing small bet
    print("\nScenario 5: Top Pair on Flop - Facing Small Bet")
    print("-" * 50)
    
    my_player_5 = {
        'hole_cards': ['Ah', 'Qd'],
        'cards': ['Ah', 'Qd'],
        'stack': '12.00',
        'bet': '0.25',  # Small bet from us
        'chips': 12.00,
        'current_bet': 0.25,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (2, "Pair of Aces", [14, 14])  # Top pair
    }
    
    table_data_5 = {
        'community_cards': ['As', '8h', '3c'],  # Top pair with good kicker
        'pot_size': '3.25',
        'current_bet_level': 0.75,
        'game_stage': 'Flop'
    }
    
    all_players_5 = [
        my_player_5,
        {'chips': 18.0, 'current_bet': 0.75, 'is_active': True, 'bet': '0.75'}  # Small bet
    ]
    
    try:
        decision5 = decision_engine.make_decision(my_player_5, table_data_5, all_players_5)
        print(f"Decision with top pair vs small bet: {decision5}")
        print("Expected: Should call or raise (strong hand)")
        
    except Exception as e:
        print(f"Error in scenario 5: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 6: Marginal Hand (A5s) Preflop - facing 3-bet
    print("\nScenario 6: Marginal Hand (A5s) Preflop - Facing 3-bet")
    print("-" * 50)
    
    my_player_6 = {
        'hole_cards': ['As', '5s'],
        'cards': ['As', '5s'],
        'stack': '12.50',
        'bet': '0.08',  # We've raised
        'chips': 12.50,
        'current_bet': 0.08,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "Ace High", [14, 5])
    }
    
    table_data_6 = {
        'community_cards': [],
        'pot_size': '0.35',
        'current_bet_level': 0.24,  # 3-bet
        'game_stage': 'Preflop'
    }
    
    all_players_6 = [
        my_player_6,
        {'chips': 15.0, 'current_bet': 0.24, 'is_active': True, 'bet': '0.24'}  # 3-bettor
    ]
    
    try:
        decision6 = decision_engine.make_decision(my_player_6, table_data_6, all_players_6)
        print(f"Decision with A5s vs 3-bet: {decision6}")
        print("Expected: Should fold (marginal hand vs 3-bet)")
        
    except Exception as e:
        print(f"Error in scenario 6: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 7: Can check scenarios
    print("\nScenario 7: Three of a Kind - Can Check (Value Betting Opportunity)")
    print("-" * 50)
    
    my_player_7 = {
        'hole_cards': ['7s', '7h'],
        'cards': ['7s', '7h'],
        'stack': '30.00',
        'bet': '0.0',
        'chips': 30.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (4, "Three of a Kind", [7, 7, 7])
    }
    
    table_data_7 = {
        'community_cards': ['7d', 'Ks', '2c', 'Jd'],
        'pot_size': '8.00',
        'current_bet_level': 0.00,  # No betting this round
        'game_stage': 'Turn'
    }
    
    all_players_7 = [
        my_player_7,
        {'chips': 20.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}  # Checking
    ]
    
    try:
        decision7 = decision_engine.make_decision(my_player_7, table_data_7, all_players_7)
        print(f"Decision with trips (can check): {decision7}")
        print("Expected: Should bet for value")
        
    except Exception as e:
        print(f"Error in scenario 7: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 8: Bluff opportunity
    print("\nScenario 8: Weak Hand on River - Bluff Opportunity")
    print("-" * 50)
    
    my_player_8 = {
        'hole_cards': ['6s', '2d'],
        'cards': ['6s', '2d'],
        'stack': '15.00',
        'bet': '0.0',
        'chips': 15.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "High Card", [6, 2])  # Very weak
    }
    
    table_data_8 = {
        'community_cards': ['As', 'Kc', 'Qh', 'Jd', '9s'],  # Scary board
        'pot_size': '8.00',
        'current_bet_level': 0.00,
        'game_stage': 'River'
    }
    
    all_players_8 = [
        my_player_8,
        {'chips': 12.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
    ]
    
    try:
        decision8 = decision_engine.make_decision(my_player_8, table_data_8, all_players_8)
        print(f"Decision with weak hand (bluff opportunity): {decision8}")
        print("Expected: Might bluff or check")
        
    except Exception as e:
        print(f"Error in scenario 8: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 60)
    print("IMPROVED TESTING COMPLETE!")
    print("=" * 60)
    print("Analysis:")
    print("- Tested situations with actual bets to call")
    print("- Verified different hand strengths vs various bet sizes")
    print("- Checked can_check situations for value betting")
    print("- Evaluated bluffing opportunities")
    print("- Tested marginal decisions")
    print("=" * 60)

if __name__ == "__main__":
    test_improved_scenarios()
