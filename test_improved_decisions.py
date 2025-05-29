#!/usr/bin/env python3
"""
Test script to validate the improved decision-making logic
"""

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_decision_improvements():
    """Test the various decision-making improvements"""
    
    decision_engine = DecisionEngine()
    hand_evaluator = HandEvaluator()
    
    print("=" * 60)
    print("TESTING IMPROVED DECISION MAKING")
    print("=" * 60)
    
    # Test case 1: A4 suited preflop (should not fold immediately)
    print("\n1. Testing A4 suited preflop:")
    my_player_a4s = {
        'has_turn': True,
        'cards': ['A♥', '4♥'],
        'hand_evaluation': (0, "A4 suited", [14, 4]),
        'stack': '0.71',
        'bet': '0.01',
        'bet_to_call': 0.02
    }
    
    table_data_preflop = {
        'pot_size': '0.03',
        'game_stage': 'Preflop',
        'community_cards': []
    }
    
    all_players_a4s = [
        my_player_a4s,
        {'is_empty': False, 'name': 'opponent1', 'bet': '0.02'},
        {'is_empty': False, 'name': 'opponent2', 'bet': '0.01'}
    ]
    
    action, amount = decision_engine.make_decision(my_player_a4s, table_data_preflop, all_players_a4s)
    print(f"   A4 suited decision: {action} for {amount}")
    print(f"   Expected: Should call or raise, not fold")
    
    # Test case 2: Pocket 8s preflop (should not fold)
    print("\n2. Testing pocket 8s preflop:")
    my_player_88 = {
        'has_turn': True,
        'cards': ['8♥', '8♠'],
        'hand_evaluation': (2, "Pair of 8s", [8, 8]),
        'stack': '0.66',
        'bet': '0.02',
        'bet_to_call': 0.04
    }
    
    table_data_88 = {
        'pot_size': '0.07',
        'game_stage': 'Preflop',
        'community_cards': []
    }
    
    all_players_88 = [
        my_player_88,
        {'is_empty': False, 'name': 'opponent1', 'bet': '0.06'},
        {'is_empty': False, 'name': 'opponent2', 'bet': '0.01'}
    ]
    
    action, amount = decision_engine.make_decision(my_player_88, table_data_88, all_players_88)
    print(f"   Pocket 8s decision: {action} for {amount}")
    print(f"   Expected: Should call or raise, not fold")
    
    # Test case 3: K9 with pair of Jacks on river (should bet for value)
    print("\n3. Testing K9 with pair of Jacks on river:")
    my_player_k9_river = {
        'has_turn': True,
        'cards': ['9♦', 'K♣'],
        'hand_evaluation': (2, "One Pair, Js", [11, 11, 13, 9, 7]),
        'stack': '0.62',
        'bet': '0.00',
        'bet_to_call': 0.00
    }
    
    table_data_river = {
        'pot_size': '0.04',
        'game_stage': 'River',
        'community_cards': ['7♠', '10♥', 'J♥', '2♣', 'J♣']
    }
    
    all_players_river = [
        my_player_k9_river,
        {'is_empty': False, 'name': 'opponent1', 'bet': '0.00'}
    ]
    
    action, amount = decision_engine.make_decision(my_player_k9_river, table_data_river, all_players_river)
    print(f"   K9 with pair of Jacks decision: {action} for {amount}")
    print(f"   Expected: Should bet for value, not check")
    
    # Test case 4: Strong hand should be more aggressive
    print("\n4. Testing premium hand aggression:")
    my_player_premium = {
        'has_turn': True,
        'cards': ['A♠', 'A♣'],
        'hand_evaluation': (2, "Pair of As", [14, 14]),
        'stack': '1.00',
        'bet': '0.02',
        'bet_to_call': 0.00
    }
    
    table_data_premium = {
        'pot_size': '0.03',
        'game_stage': 'Preflop',
        'community_cards': []
    }
    
    all_players_premium = [
        my_player_premium,
        {'is_empty': False, 'name': 'opponent1', 'bet': '0.01'}
    ]
    
    action, amount = decision_engine.make_decision(my_player_premium, table_data_premium, all_players_premium)
    print(f"   Pocket Aces decision: {action} for {amount}")
    print(f"   Expected: Should raise aggressively")
    
    print("\n" + "=" * 60)
    print("IMPROVEMENT SUMMARY:")
    print("- Enhanced hand categorization (more hands playable)")
    print("- Lower folding thresholds for decent hands")
    print("- Better postflop value betting")
    print("- More aggressive with strong hands")
    print("- Improved all-in calling ranges")
    print("=" * 60)

if __name__ == "__main__":
    test_decision_improvements()
