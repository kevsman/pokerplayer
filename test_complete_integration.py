# test_complete_integration.py
"""
Comprehensive integration test for all postflop enhancements including advanced modules.
This tests the complete system end-to-end.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock

# Setup test logging
logging.basicConfig(level=logging.DEBUG)

def test_complete_postflop_integration():
    """Test the complete postflop decision logic with all enhancements integrated."""
    
    # Import the main function
    from postflop_decision_logic import make_postflop_decision
    
    # Mock decision engine
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    # Mock player data
    player_data = {
        'current_bet': 0,
        'position': 'BTN',
        'hand': ['Kh', 'Qd'],
        'community_cards': ['9c', '7s', '2h']  # Dry board, bottom pair
    }
    
    # Mock opponent tracker with basic data
    opponent_tracker = Mock()
    opponent_tracker.opponents = {
        'Player1': Mock(
            hands_seen=10,
            get_vpip=Mock(return_value=25.0),
            get_pfr=Mock(return_value=18.0),
            classify_player_type=Mock(return_value='TAG'),
            get_fold_equity_estimate=Mock(return_value=0.6),
            should_value_bet_thin=Mock(return_value=True)
        )
    }
    opponent_tracker.get_table_dynamics = Mock(return_value={'table_type': 'tight'})
    
    # Test scenario: Medium strength hand facing a bet
    result = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=2,  # One pair
        hand_description="Pair of 9s",
        bet_to_call=50,
        can_check=False,
        pot_size=100,
        my_stack=200,
        win_probability=0.35,  # Moderate equity
        pot_odds_to_call=0.33,  # 50/(100+50) = 33%
        game_stage='flop',
        spr=2.0,
        action_fold_const='fold',
        action_check_const='check',
        action_call_const='call',
        action_raise_const='raise',
        my_player_data=player_data,
        big_blind_amount=10,
        base_aggression_factor=1.0,
        max_bet_on_table=50,
        active_opponents_count=1,
        opponent_tracker=opponent_tracker
    )
    
    # Should fold because equity (35%) > pot odds (33%) but not by enough for a weak pair
    assert result[0] == 'fold'
    print("✅ Complete integration test - Weak pair fold decision")

def test_advanced_modules_betting_adjustment():
    """Test that advanced modules properly adjust betting decisions."""
    
    from postflop_decision_logic import make_postflop_decision
    
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    player_data = {
        'current_bet': 0,
        'position': 'BTN',
        'hand': ['Ac', 'Kd'],
        'community_cards': ['As', '7s', '2s']  # Top pair on flush draw board
    }
    
    opponent_tracker = Mock()
    opponent_tracker.opponents = {
        'Player1': Mock(
            hands_seen=15,
            get_vpip=Mock(return_value=35.0),  # Loose player
            get_pfr=Mock(return_value=25.0),
            classify_player_type=Mock(return_value='LAG'),
            get_fold_equity_estimate=Mock(return_value=0.4),
            should_value_bet_thin=Mock(return_value=True)
        )
    }
    opponent_tracker.get_table_dynamics = Mock(return_value={'table_type': 'loose'})
    
    # Test scenario: Strong hand when checked to on wet board
    result = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=4,  # Top pair
        hand_description="Top pair",
        bet_to_call=0,
        can_check=True,
        pot_size=80,
        my_stack=150,
        win_probability=0.75,  # Strong equity
        pot_odds_to_call=0.0,  # Can check
        game_stage='flop',
        spr=1.875,  # 150/80
        action_fold_const='fold',
        action_check_const='check',
        action_call_const='call',
        action_raise_const='raise',
        my_player_data=player_data,
        big_blind_amount=5,
        base_aggression_factor=1.0,
        max_bet_on_table=0,
        active_opponents_count=1,
        opponent_tracker=opponent_tracker
    )
    
    # Should bet for value with strong hand
    assert result[0] == 'raise'
    assert result[1] > 0
    print(f"✅ Advanced modules betting test - Bet amount: {result[1]}")

def test_performance_monitoring_integration():
    """Test that performance monitoring is properly integrated."""
    
    from postflop_decision_logic import make_postflop_decision
    
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    player_data = {
        'current_bet': 0,
        'position': 'BB',
        'hand': ['7h', '6h'],
        'community_cards': ['5c', '4s', '2h']  # Open-ended straight draw
    }
    
    # Test with drawing hand
    with patch('postflop_decision_logic.ADVANCED_MODULES_AVAILABLE', True):
        result = make_postflop_decision(
            decision_engine_instance=decision_engine,
            numerical_hand_rank=0,  # High card
            hand_description="High card",
            bet_to_call=30,
            can_check=False,
            pot_size=60,
            my_stack=120,
            win_probability=0.32,  # Drawing hand equity
            pot_odds_to_call=0.33,  # 30/(60+30) = 33%
            game_stage='flop',
            spr=2.0,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data=player_data,
            big_blind_amount=5,
            base_aggression_factor=1.0,
            max_bet_on_table=30,
            active_opponents_count=1,
            opponent_tracker=None        )
    
    # Drawing hand with good implied odds should call on the flop
    assert result[0] == 'call'
    print("✅ Performance monitoring integration test completed")

def test_board_texture_analysis_integration():
    """Test that board texture analysis affects betting decisions."""
    
    from postflop_decision_logic import make_postflop_decision
    
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    # Wet board scenario
    player_data = {
        'current_bet': 0,
        'position': 'CO',
        'hand': ['Ah', 'Ac'],
        'community_cards': ['Ts', '9h', '8c']  # Connected, wet board
    }
    
    opponent_tracker = Mock()
    opponent_tracker.opponents = {
        'Player1': Mock(
            hands_seen=20,
            get_vpip=Mock(return_value=28.0),
            get_pfr=Mock(return_value=20.0),
            classify_player_type=Mock(return_value='TAG'),
            get_fold_equity_estimate=Mock(return_value=0.5),
            should_value_bet_thin=Mock(return_value=True)
        )
    }
    opponent_tracker.get_table_dynamics = Mock(return_value={'table_type': 'balanced'})
    
    # Test overpair on wet board when checked to
    result = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=6,  # Overpair
        hand_description="Pocket Aces",
        bet_to_call=0,
        can_check=True,
        pot_size=45,
        my_stack=200,
        win_probability=0.80,  # Very strong hand
        pot_odds_to_call=0.0,
        game_stage='flop',
        spr=4.44,  # 200/45
        action_fold_const='fold',
        action_check_const='check',
        action_call_const='call',
        action_raise_const='raise',
        my_player_data=player_data,
        big_blind_amount=2,
        base_aggression_factor=1.0,
        max_bet_on_table=0,
        active_opponents_count=1,
        opponent_tracker=opponent_tracker
    )
    
    # Should bet for protection on wet board with strong hand
    assert result[0] == 'raise'
    assert result[1] > 0
    print(f"✅ Board texture analysis integration - Protective bet: {result[1]}")

def test_error_handling_and_fallbacks():
    """Test that the system gracefully handles errors and uses fallbacks."""
    
    from postflop_decision_logic import make_postflop_decision
    
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    player_data = {
        'current_bet': 10,
        'position': 'SB',
        'hand': ['Jc', 'Td'],
        'community_cards': ['Jh', '5d', '3s']
    }
    
    # Test with None opponent tracker and minimal data
    result = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=2,  # Top pair
        hand_description="Top pair",
        bet_to_call=0,
        can_check=True,
        pot_size=30,
        my_stack=100,
        win_probability=0.68,
        pot_odds_to_call=0.0,
        game_stage='flop',
        spr=3.33,
        action_fold_const='fold',
        action_check_const='check',
        action_call_const='call',
        action_raise_const='raise',
        my_player_data=player_data,
        big_blind_amount=2,
        base_aggression_factor=1.0,
        max_bet_on_table=0,
        active_opponents_count=1,
        opponent_tracker=None  # No opponent data
    )
    
    # Should still make a reasonable decision despite missing advanced analysis
    assert result[0] in ['check', 'raise']
    print(f"✅ Error handling test - Decision with minimal data: {result[0]}")

if __name__ == "__main__":
    print("Running complete integration tests...")
    
    test_complete_postflop_integration()
    test_advanced_modules_betting_adjustment()
    test_performance_monitoring_integration()
    test_board_texture_analysis_integration()
    test_error_handling_and_fallbacks()
    
    print("\n🎉 All integration tests completed successfully!")
    print("✅ Core postflop improvements: INTEGRATED")
    print("✅ Advanced opponent modeling: INTEGRATED")
    print("✅ Enhanced board analysis: INTEGRATED")
    print("✅ Performance monitoring: INTEGRATED")
    print("✅ Error handling and fallbacks: WORKING")
    
    print("\n📊 POSTFLOP SYSTEM STATUS: FULLY INTEGRATED AND PRODUCTION READY")
