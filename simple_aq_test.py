import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hand_utils import get_preflop_hand_category

# Test AQ offsuit categorization
hand = ['Ah', 'Qc']
position = 'CO'
category = get_preflop_hand_category(hand, position)
print(f"AQ offsuit categorized as: {category}")

# Now test the decision logic
from preflop_decision_logic import make_preflop_decision

my_player = {'hand': ['Ah', 'Qc'], 'stack': 1.0, 'current_bet': 0.0}

action, amount = make_preflop_decision(
    my_player=my_player,
    hand_category=category,
    position='CO',
    bet_to_call=0.16,
    can_check=False,
    my_stack=1.0,
    pot_size=0.27,
    active_opponents_count=2,
    small_blind=0.01,
    big_blind=0.02,
    my_current_bet_this_street=0.0,
    max_bet_on_table=0.18,
    min_raise=0.04,
    is_sb=False,
    is_bb=False,
    action_fold_const="fold",
    action_check_const="check",
    action_call_const="call",
    action_raise_const="raise"
)

print(f"Decision: {action}, Amount: {amount}")

# Calculate pot odds for verification
pot_odds_needed = 0.16 / (0.27 + 0.16)
print(f"Pot odds needed: {pot_odds_needed:.1%}")
print(f"AQ offsuit should call with {pot_odds_needed:.1%} pot odds")
