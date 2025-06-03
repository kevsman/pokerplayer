#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced poker bot decision engine.
Tests various scenarios to ensure the bot is performing optimally.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from html_parser_original import PokerPageParser
from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_comprehensive_scenarios():
    """Test decision engine with manually created scenarios"""
    print("=" * 60)
    print("COMPREHENSIVE POKER BOT TESTING")
    print("=" * 60)
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)
    
    # Scenario 1: Strong preflop hand (pocket aces)
    print("\nScenario 1: Pocket Aces Preflop")
    print("-" * 40)
    
    my_player_1 = {
        'hole_cards': ['As', 'Ah'],
        'cards': ['As', 'Ah'],
        'stack': '14.96',
        'bet': '0.01',
        'chips': 14.96,
        'current_bet': 0.01,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (2, "Pair of Aces", [14, 14])
    }
    
    table_data_1 = {
        'community_cards': [],
        'pot_size': '0.03',
        'current_bet_level': 0.02,
        'game_stage': 'Preflop'
    }
    
    all_players_1 = [
        my_player_1,
        {'chips': 10.0, 'current_bet': 0.02, 'is_active': True, 'bet': '0.02'},
        {'chips': 8.5, 'current_bet': 0.01, 'is_active': True, 'bet': '0.01'}
    ]
    
    try:
        decision1 = decision_engine.make_decision(my_player_1, table_data_1, all_players_1)
        print(f"Decision with pocket aces: {decision1}")
        print("Expected: Should raise aggressively")
        
    except Exception as e:
        print(f"Error in scenario 1: {e}")
        import traceback
        traceback.print_exc()
    
    # Scenario 2: Weak hand facing large bet
    print("\nScenario 2: Weak Hand (7-2 offsuit) facing large bet")
    print("-" * 40)
    
    my_player_2 = {
        'hole_cards': ['7s', '2h'],
        'cards': ['7s', '2h'],
        'stack': '10.00',
        'bet': '0.0',
        'chips': 10.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "High Card", [7, 2])
    }
    
    table_data_2 = {
        'community_cards': ['Kd', 'Qc', 'Js'],
        'pot_size': '2.50',
        'current_bet_level': 5.00,
        'game_stage': 'Flop'
    }
    
    all_players_2 = [
        my_player_2,
        {'chips': 15.0, 'current_bet': 5.00, 'is_active': True, 'bet': '5.00'}
    ]
    
    try:
        decision2 = decision_engine.make_decision(my_player_2, table_data_2, all_players_2)
        print(f"Decision with 7-2 vs large bet: {decision2}")
        print("Expected: Should fold")
        
    except Exception as e:
        print(f"Error in scenario 2: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 3: Very strong hand (Full House) on the river, facing a bet
    print("\nScenario 3: Full House on River, Facing Bet")
    print("-" * 40)
    
    my_player_3 = {
        'hole_cards': ['Ah', 'Kd'],
        'cards': ['Ah', 'Kd'],
        'stack': '20.00',
        'bet': '0.0',
        'chips': 20.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (7, "Full House", [14, 13])
    }
    
    table_data_3 = {
        'community_cards': ['As', 'Kc', 'Kh', 'Qh', 'Ad'],
        'pot_size': '15.00',
        'current_bet_level': 5.00,
        'game_stage': 'River'
    }
    
    all_players_3 = [
        my_player_3,
        {'chips': 25.0, 'current_bet': 5.00, 'is_active': True, 'bet': '5.00'}
    ]
    
    try:
        decision3 = decision_engine.make_decision(my_player_3, table_data_3, all_players_3)
        print(f"Decision with Full House on River: {decision3}")
        print("Expected: Should raise/reraise aggressively")
        
    except Exception as e:
        print(f"Error in scenario 3: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 4: Strong hand (Three of a Kind) on the turn, can check
    print("\nScenario 4: Three of a Kind on Turn, Can Check")
    print("-" * 40)
    
    my_player_4 = {
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
    
    table_data_4 = {
        'community_cards': ['7d', 'Ks', '2c', 'Jd'],
        'pot_size': '8.00',
        'current_bet_level': 0.00,
        'game_stage': 'Turn'
    }
    
    all_players_4 = [
        my_player_4,
        {'chips': 20.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
    ]
    
    try:
        decision4 = decision_engine.make_decision(my_player_4, table_data_4, all_players_4)
        print(f"Decision with Three of a Kind on Turn (can check): {decision4}")
        print("Expected: Should bet for value")
        
    except Exception as e:
        print(f"Error in scenario 4: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 5: Medium hand (Pair) on the flop, facing a small bet
    print("\nScenario 5: Pair on Flop, Facing Small Bet")
    print("-" * 40)
    
    my_player_5 = {
        'hole_cards': ['Td', '9s'],
        'cards': ['Td', '9s'],
        'stack': '12.00',
        'bet': '0.0',
        'chips': 12.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (2, "One Pair", [10, 10])
    }
    
    table_data_5 = {
        'community_cards': ['Ts', '5h', '2c'],
        'pot_size': '3.00',
        'current_bet_level': 0.50,
        'game_stage': 'Flop'
    }
    
    all_players_5 = [
        my_player_5,
        {'chips': 18.0, 'current_bet': 0.50, 'is_active': True, 'bet': '0.50'}
    ]
    
    try:
        decision5 = decision_engine.make_decision(my_player_5, table_data_5, all_players_5)
        print(f"Decision with Pair on Flop (facing small bet): {decision5}")
        print("Expected: Should call or raise")
        
    except Exception as e:
        print(f"Error in scenario 5: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 6: Drawing hand (Flush Draw) on the turn, facing a bet
    print("\nScenario 6: Flush Draw on Turn, Facing Bet")
    print("-" * 40)
    
    my_player_6 = {
        'hole_cards': ['Ah', 'Kh'],
        'cards': ['Ah', 'Kh'],
        'stack': '15.00',
        'bet': '0.0',
        'chips': 15.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "Ace High", [14, 13])
    }
    
    table_data_6 = {
        'community_cards': ['Qh', '7h', '2s', 'Jd'],
        'pot_size': '6.00',
        'current_bet_level': 2.00,
        'game_stage': 'Turn'
    }
    
    all_players_6 = [
        my_player_6,
        {'chips': 20.0, 'current_bet': 2.00, 'is_active': True, 'bet': '2.00'}
    ]
    
    try:
        decision6 = decision_engine.make_decision(my_player_6, table_data_6, all_players_6)
        print(f"Decision with Flush Draw on Turn (facing bet): {decision6}")
        print("Expected: Should call with good pot odds")
        
    except Exception as e:
        print(f"Error in scenario 6: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 7: Weak hand on the river, can check, opportunity to bluff
    print("\nScenario 7: Weak Hand on River, Can Check, Bluff Opportunity")
    print("-" * 40)
    
    my_player_7 = {
        'hole_cards': ['7s', '2d'],
        'cards': ['7s', '2d'],
        'stack': '10.00',
        'bet': '0.0',
        'chips': 10.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "High Card", [7, 2])
    }
    
    table_data_7 = {
        'community_cards': ['As', 'Kc', 'Qh', 'Jd', '3s'],
        'pot_size': '5.00',
        'current_bet_level': 0.00,
        'game_stage': 'River'
    }
    
    all_players_7 = [
        my_player_7,
        {'chips': 10.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
    ]
    
    try:
        decision_engine.big_blind = 0.02
        decision7 = decision_engine.make_decision(my_player_7, table_data_7, all_players_7)
        print(f"Decision with Weak Hand on River (can check, bluff opp): {decision7}")
        print("Expected: Might bluff or check")
        
    except Exception as e:
        print(f"Error in scenario 7: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 8: Medium hand on the river, can check, good win probability
    print("\nScenario 8: Medium Hand on River, Can Check, Good Win Rate")
    print("-" * 40)
    
    my_player_8 = {
        'hole_cards': ['Ac', 'Ts'],
        'cards': ['Ac', 'Ts'],
        'stack': '18.00',
        'bet': '0.0',
        'chips': 18.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (3, "Two Pair", [14, 10])
    }
    
    table_data_8 = {
        'community_cards': ['Ah', 'Td', '2c', '5s', '7h'],
        'pot_size': '9.00',
        'current_bet_level': 0.00,
        'game_stage': 'River'
    }
    
    all_players_8 = [
        my_player_8,
        {'chips': 15.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
    ]
    
    try:
        decision_engine.big_blind = 0.02
        decision8 = decision_engine.make_decision(my_player_8, table_data_8, all_players_8)
        print(f"Decision with Medium Hand on River (can check, good win rate): {decision8}")
        print("Expected: Should bet for value")
        
    except Exception as e:
        print(f"Error in scenario 8: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 9: Marginal hand preflop, facing a raise
    print("\nScenario 9: Marginal Hand Preflop (A5 suited), Facing Raise")
    print("-" * 40)
    
    my_player_9 = {
        'hole_cards': ['As', '5s'],
        'cards': ['As', '5s'],
        'stack': '12.50',
        'bet': '0.02',
        'chips': 12.50,
        'current_bet': 0.02,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "Ace High", [14, 5])
    }
    
    table_data_9 = {
        'community_cards': [],
        'pot_size': '0.15',
        'current_bet_level': 0.08,
        'game_stage': 'Preflop'
    }
    
    all_players_9 = [
        my_player_9,
        {'chips': 15.0, 'current_bet': 0.08, 'is_active': True, 'bet': '0.08'}
    ]
    
    try:
        decision9 = decision_engine.make_decision(my_player_9, table_data_9, all_players_9)
        print(f"Decision with A5 suited vs raise: {decision9}")
        print("Expected: Should call or fold depending on pot odds")
        
    except Exception as e:
        print(f"Error in scenario 9: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 10: Strong draw on flop, facing large bet
    print("\nScenario 10: Strong Draw on Flop (straight + flush draw)")
    print("-" * 40)
    
    my_player_10 = {
        'hole_cards': ['9h', '8h'],
        'cards': ['9h', '8h'],
        'stack': '20.00',
        'bet': '0.0',
        'chips': 20.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "Nine High", [9, 8])
    }
    
    table_data_10 = {
        'community_cards': ['7h', '6s', '5h'],
        'pot_size': '4.00',
        'current_bet_level': 3.00,
        'game_stage': 'Flop'
    }
    
    all_players_10 = [
        my_player_10,
        {'chips': 25.0, 'current_bet': 3.00, 'is_active': True, 'bet': '3.00'}
    ]
    
    try:
        decision10 = decision_engine.make_decision(my_player_10, table_data_10, all_players_10)
        print(f"Decision with strong draw vs large bet: {decision10}")
        print("Expected: Should call or raise with strong draw")
        
    except Exception as e:
        print(f"Error in scenario 10: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 60)
    print("COMPREHENSIVE TESTING COMPLETE!")
    print("=" * 60)
    print("Summary:")
    print("- Tested premium hands (should be aggressive)")
    print("- Tested weak hands (should fold to large bets)")
    print("- Tested strong made hands (should value bet)")
    print("- Tested drawing hands (should consider pot odds)")
    print("- Tested bluffing opportunities")
    print("- Tested marginal situations")
    print("=" * 60)

if __name__ == "__main__":
    test_comprehensive_scenarios()
