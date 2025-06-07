#!/usr/bin/env python3
"""
Test script to validate postflop decision logic integration with advanced features.
"""

import unittest
from unittest.mock import Mock
from postflop_decision_logic import make_postflop_decision
from decision_engine import DecisionEngine
from opponent_tracking import OpponentTracker


class TestPostflopIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment."""
        self.decision_engine = DecisionEngine()
        self.opponent_tracker = OpponentTracker()
        
        # Mock player data
        self.player_data = {
            'current_bet': 0,
            'hand': ['Kh', 'Ks'],
            'community_cards': ['Ah', '7c', '2d']
        }
    
    def test_very_strong_hand_betting(self):
        """Test betting with very strong hands."""
        action, amount = make_postflop_decision(
            decision_engine_instance=self.decision_engine,
            numerical_hand_rank=7,  # Very strong
            hand_description="Pocket Kings",
            bet_to_call=0,
            can_check=True,
            pot_size=100,
            my_stack=500,
            win_probability=0.90,
            pot_odds_to_call=0.0,
            game_stage='flop',
            spr=5.0,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data=self.player_data,
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=0,
            active_opponents_count=1,
            opponent_tracker=self.opponent_tracker
        )
        
        self.assertIn(action, ['raise', 'check'])
        if action == 'raise':
            self.assertGreater(amount, 0)
        print(f"✓ Very strong hand test: {action} {amount}")
    
    def test_medium_hand_facing_bet(self):
        """Test medium strength hand facing a bet."""
        action, amount = make_postflop_decision(
            decision_engine_instance=self.decision_engine,
            numerical_hand_rank=3,  # Medium strength
            hand_description="Middle Pair",
            bet_to_call=50,
            can_check=False,
            pot_size=100,
            my_stack=400,
            win_probability=0.55,
            pot_odds_to_call=0.33,
            game_stage='turn',
            spr=4.0,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data=self.player_data,
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=50,
            active_opponents_count=1,
            opponent_tracker=self.opponent_tracker
        )
        
        self.assertIn(action, ['call', 'fold', 'raise'])
        print(f"✓ Medium hand vs bet test: {action} {amount}")
    
    def test_weak_hand_drawing(self):
        """Test weak hand with drawing potential."""
        action, amount = make_postflop_decision(
            decision_engine_instance=self.decision_engine,
            numerical_hand_rank=1,  # Weak
            hand_description="Flush Draw",
            bet_to_call=30,
            can_check=False,
            pot_size=120,
            my_stack=300,
            win_probability=0.35,  # Drawing hand equity
            pot_odds_to_call=0.20,
            game_stage='flop',
            spr=2.5,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data=self.player_data,
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=30,
            active_opponents_count=1,
            opponent_tracker=self.opponent_tracker
        )
        
        self.assertIn(action, ['call', 'fold'])
        print(f"✓ Drawing hand test: {action} {amount}")
    
    def test_spr_strategy_integration(self):
        """Test SPR strategy adjustments."""
        # Low SPR test
        action, amount = make_postflop_decision(
            decision_engine_instance=self.decision_engine,
            numerical_hand_rank=5,  # Strong
            hand_description="Top Pair",
            bet_to_call=0,
            can_check=True,
            pot_size=200,
            my_stack=150,  # Low SPR scenario
            win_probability=0.75,
            pot_odds_to_call=0.0,
            game_stage='flop',
            spr=0.75,  # Very low SPR
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data=self.player_data,
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=0,
            active_opponents_count=1,
            opponent_tracker=self.opponent_tracker
        )
        
        print(f"✓ Low SPR strategy test: {action} {amount}")
    
    def test_opponent_tracking_integration(self):
        """Test integration with opponent tracking data."""
        # Add opponent data
        self.opponent_tracker.add_hand_data('Villain1', {
            'preflop_action': 'raise',
            'position': 'BTN',
            'vpip': True,
            'pfr': True,
            'hand_shown': None
        })
        
        action, amount = make_postflop_decision(
            decision_engine_instance=self.decision_engine,
            numerical_hand_rank=4,  # Strong
            hand_description="Two Pair",
            bet_to_call=0,
            can_check=True,
            pot_size=80,
            my_stack=400,
            win_probability=0.80,
            pot_odds_to_call=0.0,
            game_stage='river',
            spr=5.0,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data=self.player_data,
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=0,
            active_opponents_count=1,
            opponent_tracker=self.opponent_tracker
        )
        
        print(f"✓ Opponent tracking integration test: {action} {amount}")


def main():
    print("============================================================")
    print("POSTFLOP DECISION LOGIC INTEGRATION TESTS")
    print("============================================================")
    
    # Run the tests
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
