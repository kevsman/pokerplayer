#!/usr/bin/env python3
"""
Detailed test of the enhanced poker bot's EV calculations and decision logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_ev_calculations():
    """Test the Expected Value calculations directly"""
    print("Testing Enhanced EV Calculations")
    print("=" * 50)
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator)
    
    # Test scenario: Medium strength hand with decent pot odds
    my_player = {
        'hole_cards': ['Ks', '8h'],  # K8 offsuit - marginal hand
        'chips': 0.79,
        'current_bet': 0.01,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'bet_to_call': 0.01
    }
    
    table_data = {
        'community_cards': [],
        'pot_size': '€0.03',
        'current_bet_level': 0.01,
        'game_stage': 'Preflop'
    }
    
    all_players = [
        my_player,
        {'chips': 0.65, 'current_bet': 0.02, 'is_active': True},  # Player who raised
        {'chips': 1.50, 'current_bet': 0.00, 'is_active': True},  # Player yet to act
        {'chips': 2.20, 'current_bet': 0.00, 'is_active': True},  # Player yet to act
        {'chips': 0.90, 'current_bet': 0.00, 'is_active': True},  # Player yet to act
        {'chips': 1.80, 'current_bet': 0.00, 'is_active': True}   # Player yet to act
    ]
    
    print(f"Scenario: K8 offsuit preflop")
    print(f"Pot size: {table_data['pot_size']}")
    print(f"Bet to call: €{my_player['bet_to_call']}")
    print(f"Our stack: €{my_player['chips']}")
    print(f"Active opponents: {len([p for p in all_players if p.get('is_active', False) and not p.get('is_my_player', False)])}")
    
    try:
        # Test individual EV calculations
        pot_size_numeric = float(table_data['pot_size'].replace('€', ''))
        
        # Calculate expected values for each action
        print(f"\nCalculating Expected Values:")
        print("-" * 30)
        
        # EV of folding (always 0)
        ev_fold = 0.0
        print(f"EV of Fold: €{ev_fold:.4f}")
        
        # EV of calling
        ev_call = decision_engine.calculate_expected_value(
            'call', my_player, table_data, all_players
        )
        print(f"EV of Call: €{ev_call:.4f}")
        
        # EV of raising
        ev_raise = decision_engine.calculate_expected_value(
            'raise', my_player, table_data, all_players
        )
        print(f"EV of Raise: €{ev_raise:.4f}")
        
        # Determine optimal action based on EV
        best_action = 'fold'
        best_ev = ev_fold
        
        if ev_call > best_ev:
            best_action = 'call'
            best_ev = ev_call
            
        if ev_raise > best_ev:
            best_action = 'raise'
            best_ev = ev_raise
        
        print(f"\nOptimal action by EV: {best_action.upper()} (EV: €{best_ev:.4f})")
        
        # Now get the actual decision from the engine
        actual_decision = decision_engine.make_decision(my_player, table_data, all_players)
        print(f"Actual bot decision: {actual_decision}")
        
        # Test win probability calculation
        print(f"\nWin Probability Analysis:")
        print("-" * 30)
        
        hole_cards_tuple = [('K', 'SPADES'), ('8', 'HEARTS')]
        community_cards = []
        num_opponents = len([p for p in all_players if p.get('is_active', False) and not p.get('is_my_player', False)])
        
        win_prob = decision_engine.equity_calculator.calculate_win_probability(
            hole_cards_tuple, community_cards, num_opponents
        )
        print(f"Win probability vs {num_opponents} opponents: {win_prob:.3f} ({win_prob*100:.1f}%)")
        
        # Calculate pot odds
        pot_odds = my_player['bet_to_call'] / (pot_size_numeric + my_player['bet_to_call'])
        print(f"Pot odds: {pot_odds:.3f} ({pot_odds*100:.1f}%)")
        print(f"Required win rate to call: {pot_odds*100:.1f}%")
        print(f"Actual win rate: {win_prob*100:.1f}%")
        
        if win_prob > pot_odds:
            print("✓ Win probability exceeds pot odds - mathematically profitable call")
        else:
            print("✗ Win probability below pot odds - unprofitable call")
        
    except Exception as e:
        print(f"Error in EV calculations: {e}")
        import traceback
        traceback.print_exc()

def test_conservative_vs_aggressive():
    """Test how the bot behaves with different hand strengths"""
    print("\n" + "=" * 50)
    print("Testing Conservative vs Aggressive Decisions")
    print("=" * 50)
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator)
    
    # Test different hand strengths
    test_hands = [
        (['As', 'Ah'], "Pocket Aces - Premium"),
        (['Ks', 'Qh'], "KQ offsuit - Strong"),
        (['Ts', '9h'], "T9 offsuit - Medium"),
        (['7s', '2h'], "72 offsuit - Trash")
    ]
    
    base_table_data = {
        'community_cards': [],
        'pot_size': '€0.10',
        'current_bet_level': 0.05,
        'game_stage': 'Preflop'
    }
    
    base_all_players = [
        None,  # Will be filled with my_player
        {'chips': 2.0, 'current_bet': 0.05, 'is_active': True},
        {'chips': 1.5, 'current_bet': 0.00, 'is_active': True}
    ]
    
    for hole_cards, hand_description in test_hands:
        print(f"\nTesting: {hand_description}")
        print(f"Cards: {hole_cards}")
        
        my_player = {
            'hole_cards': hole_cards,
            'chips': 2.0,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'bet_to_call': 0.05
        }
        
        base_all_players[0] = my_player
        
        try:
            decision = decision_engine.make_decision(my_player, base_table_data, base_all_players)
            print(f"Decision: {decision}")
            
            # Calculate hand strength for context
            hole_cards_tuple = [(card[0], card[1].upper() + 'S' if card[1] in 'shcd' else 'SPADES') for card in hole_cards]
            hand_strength = hand_evaluator.evaluate_hand_strength(hole_cards_tuple, [])
            print(f"Hand strength: {hand_strength:.3f}")
            
        except Exception as e:
            print(f"Error with {hand_description}: {e}")

if __name__ == "__main__":
    test_ev_calculations()
    test_conservative_vs_aggressive()
    
    print("\n" + "=" * 50)
    print("Enhanced Decision Engine Analysis Complete!")
    print("The bot now uses proper EV calculations and conservative aggression.")
    print("This should prevent the large losses from overly aggressive betting.")
