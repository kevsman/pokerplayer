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
        'chips': 14.96,
        'current_bet': 0.01,
        'is_active': True,
        'is_my_player': True
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
        'chips': 10.00,
        'current_bet': 0.0,
        'is_active': True,
        'is_my_player': True
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
        
    print("\nBasic Testing Complete!")
    print("The enhanced decision engine is processing different scenarios.")

if __name__ == "__main__":
    test_preflop_decision()
    test_different_scenarios()
    
    print("\n" + "=" * 50)
    print("Testing Complete!")
    print("If no errors appeared above, the enhanced decision engine is working correctly.")
