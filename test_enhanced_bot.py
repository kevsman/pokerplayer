#!/usr/bin/env python3
"""
Test script for the enhanced poker bot decision engine.
Tests the new EV-based decision making with the preflop example.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from html_parser import PokerPageParser
from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_preflop_decision():
    """Test the bot's decision on the preflop example"""
    print("Testing Enhanced Poker Bot Decision Engine")
    print("=" * 50)
    
    # Load the HTML file
    html_file = "examples/preflop_my_turn.html"
    print(f"Loading HTML file: {html_file}")
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {html_file}")
        return    # Parse the game state
    parser = PokerPageParser()
    parsed_result = parser.parse_html(html_content)
    
    # Extract components for decision engine
    my_player = parsed_result.get('my_player_data', {})
    table_data = parsed_result.get('table_data', {})
    all_players_data = parsed_result.get('all_players_data', [])
    
    print("\nParsed Game State:")
    print(f"Table data: {table_data}")
    print(f"My player data: {my_player}")
    print(f"Number of players: {len(all_players_data)}")
    
    # Initialize decision engine and hand evaluator
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator)
    
    print("\nMaking Decision with Enhanced Engine:")
    print("-" * 40)
    
    # Make decision
    try:
        decision = decision_engine.make_decision(my_player, table_data, all_players_data)
        print(f"Decision: {decision}")
        
    except Exception as e:
        print(f"Error making decision: {e}")
        import traceback
        traceback.print_exc()

def test_different_scenarios():
    """Test decision engine with manually created scenarios"""
    print("\n" + "=" * 50)
    print("Testing Different Poker Scenarios")
    print("=" * 50)
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator)
    
    # Scenario 1: Strong preflop hand (pocket aces)
    print("\nScenario 1: Pocket Aces Preflop")
    print("-" * 30)
      my_player_1 = {
        'hole_cards': ['As', 'Ah'],
        'cards': ['As', 'Ah'],
        'chips': 14.96,
        'current_bet': 0.01,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (2, "Pair of Aces", [14, 14])
    }
    
    table_data_1 = {
        'community_cards': [],
        'pot_size': 0.03,
        'current_bet_level': 0.02,
        'game_stage': 'preflop'
    }
    
    all_players_1 = [
        my_player_1,
        {'chips': 10.0, 'current_bet': 0.02, 'is_active': True},
        {'chips': 8.5, 'current_bet': 0.01, 'is_active': True}
    ]
    
    try:
        decision1 = decision_engine.make_decision(my_player_1, table_data_1, all_players_1)
        print(f"Decision with pocket aces: {decision1}")
        
    except Exception as e:
        print(f"Error in scenario 1: {e}")
        import traceback
        traceback.print_exc()
    
    # Scenario 2: Weak hand facing large bet
    print("\nScenario 2: Weak Hand (7-2 offsuit) facing large bet")
    print("-" * 30)
      my_player_2 = {
        'hole_cards': ['7s', '2h'],
        'cards': ['7s', '2h'],
        'chips': 10.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (1, "High Card", [7, 2])
    }
    
    table_data_2 = {
        'community_cards': ['Kd', 'Qc', 'Js'],
        'pot_size': 2.50,
        'current_bet_level': 5.00,
        'game_stage': 'flop'
    }
    
    all_players_2 = [
        my_player_2,
        {'chips': 15.0, 'current_bet': 5.00, 'is_active': True}
    ]
    
    try:
        decision2 = decision_engine.make_decision(my_player_2, table_data_2, all_players_2)
        print(f"Decision with 7-2 vs large bet: {decision2}")
        
    except Exception as e:
        print(f"Error in scenario 2: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 3: Very strong hand (Full House) on the river, facing a bet
    print("\\nScenario 3: Full House on River, Facing Bet")
    print("-" * 30)    my_player_3 = {
        'hole_cards': ['Ah', 'Kd'],
        'cards': ['Ah', 'Kd'],
        'chips': 20.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (7, "Full House", [14, 13])
    }
    table_data_3 = {
        'community_cards': ['As', 'Kc', 'Kh', 'Qh', 'Ad'], # Player has A-K, board A K K Q A -> Full House Aces full of Kings
        'pot_size': 15.00,
        'current_bet_level': 5.00, # Opponent bets 5
        'game_stage': 'river'
    }
    all_players_3 = [
        my_player_3,
        {'chips': 25.0, 'current_bet': 5.00, 'is_active': True}
    ]
    try:
        decision3 = decision_engine.make_decision(my_player_3, table_data_3, all_players_3)
        print(f"Decision with Full House on River: {decision3}")
    except Exception as e:
        print(f"Error in scenario 3: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 4: Strong hand (Three of a Kind) on the turn, can check
    print("\\nScenario 4: Three of a Kind on Turn, Can Check")
    print("-" * 30)
    my_player_4 = {
        'hole_cards': ['7s', '7h'],
        'chips': 30.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True
    }
    table_data_4 = {
        'community_cards': ['7d', 'Ks', '2c', 'Jd'], # Player has 7-7, board 7 K 2 J -> Three of a Kind
        'pot_size': 8.00,
        'current_bet_level': 0.00, # No bet, can check
        'game_stage': 'turn'
    }
    all_players_4 = [
        my_player_4,
        {'chips': 20.0, 'current_bet': 0.00, 'is_active': True}
    ]
    try:
        decision4 = decision_engine.make_decision(my_player_4, table_data_4, all_players_4)
        print(f"Decision with Three of a Kind on Turn (can check): {decision4}")
    except Exception as e:
        print(f"Error in scenario 4: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 5: Medium hand (Pair) on the flop, facing a small bet
    print("\\nScenario 5: Pair on Flop, Facing Small Bet")
    print("-" * 30)
    my_player_5 = {
        'hole_cards': ['Td', '9s'],
        'chips': 12.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True
    }
    table_data_5 = {
        'community_cards': ['Ts', '5h', '2c'], # Player has T-9, board T 5 2 -> Top Pair
        'pot_size': 3.00,
        'current_bet_level': 0.50, # Opponent bets 0.50
        'game_stage': 'flop'
    }
    all_players_5 = [
        my_player_5,
        {'chips': 18.0, 'current_bet': 0.50, 'is_active': True}
    ]
    try:
        decision5 = decision_engine.make_decision(my_player_5, table_data_5, all_players_5)
        print(f"Decision with Pair on Flop (facing small bet): {decision5}")
    except Exception as e:
        print(f"Error in scenario 5: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 6: Drawing hand (Flush Draw) on the turn, facing a bet
    print("\\nScenario 6: Flush Draw on Turn, Facing Bet")
    print("-" * 30)
    my_player_6 = {
        'hole_cards': ['Ah', 'Kh'], # Hearts
        'chips': 15.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True
    }
    table_data_6 = {
        'community_cards': ['Qh', '7h', '2s', 'Jd'], # Player has A K hearts, board Q 7 hearts, 2 spades, J diamonds -> Flush Draw
        'pot_size': 6.00,
        'current_bet_level': 2.00, # Opponent bets 2.00
        'game_stage': 'turn'
    }
    all_players_6 = [
        my_player_6,
        {'chips': 20.0, 'current_bet': 2.00, 'is_active': True}
    ]
    try:
        decision6 = decision_engine.make_decision(my_player_6, table_data_6, all_players_6)
        print(f"Decision with Flush Draw on Turn (facing bet): {decision6}")
    except Exception as e:
        print(f"Error in scenario 6: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 7: Weak hand on the river, can check, opportunity to bluff
    print("\\nScenario 7: Weak Hand on River, Can Check, Bluff Opportunity")
    print("-" * 30)
    my_player_7 = {
        'hole_cards': ['7s', '2d'],
        'chips': 10.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True
    }
    table_data_7 = {
        'community_cards': ['As', 'Kc', 'Qh', 'Jd', '3s'], # Player has 7-2, board A K Q J 3 -> Bust
        'pot_size': 5.00, # Pot is reasonably sized for a bluff
        'current_bet_level': 0.00, # Can check
        'game_stage': 'river'
    }
    all_players_7 = [
        my_player_7,
        {'chips': 10.0, 'current_bet': 0.00, 'is_active': True} # Opponent also has chips
    ]
    try:
        # Ensure big_blind is set for bluffing logic in postflop
        decision_engine.big_blind = 0.02 # Example big blind
        decision7 = decision_engine.make_decision(my_player_7, table_data_7, all_players_7)
        print(f"Decision with Weak Hand on River (can check, bluff opp): {decision7}")
    except Exception as e:
        print(f"Error in scenario 7: {e}")
        import traceback
        traceback.print_exc()

    # Scenario 8: Medium hand on the river, can check, good win probability
    print("\\nScenario 8: Medium Hand on River, Can Check, Good Win Rate")
    print("-" * 30)
    my_player_8 = {
        'hole_cards': ['Ac', 'Ts'],
        'chips': 18.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True
    }
    table_data_8 = {
        'community_cards': ['Ah', 'Td', '2c', '5s', '7h'], # Player has A-T, board A T 2 5 7 -> Two Pair (Aces and Tens)
        'pot_size': 9.00,
        'current_bet_level': 0.00, # Can check
        'game_stage': 'river'
    }
    all_players_8 = [
        my_player_8,
        {'chips': 15.0, 'current_bet': 0.00, 'is_active': True}
    ]
    try:
        decision_engine.big_blind = 0.02 # Example big blind
        decision8 = decision_engine.make_decision(my_player_8, table_data_8, all_players_8)
        print(f"Decision with Medium Hand on River (can check, good win rate): {decision8}")
    except Exception as e:
        print(f"Error in scenario 8: {e}")
        import traceback
        traceback.print_exc()
        
    print("\\nBasic Testing Complete!")
    print("The enhanced decision engine is processing different scenarios.")

if __name__ == "__main__":
    test_preflop_decision()
    test_different_scenarios()
    
    print("\n" + "=" * 50)
    print("Testing Complete!")
    print("If no errors appeared above, the enhanced decision engine is working correctly.")
