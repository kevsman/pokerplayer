from preflop_decision_logic import make_preflop_decision
from hand_utils import categorize_preflop_hand

# Test different hand categories to ensure no regression
test_cases = [
    # Test Strong Pair (should still work)
    {'hand': ['A♠', 'A♥'], 'position': 'CO', 'bet': 0.16, 'pot': 0.27, 'description': 'AA in CO'},
    # Test Playable Broadway (should still work)  
    {'hand': ['K♠', 'Q♣'], 'position': 'CO', 'bet': 0.16, 'pot': 0.27, 'description': 'KQ offsuit in CO'},
    # Test weaker Offsuit Ace (should fold)
    {'hand': ['A♠', 'J♣'], 'position': 'CO', 'bet': 0.16, 'pot': 0.27, 'description': 'AJ offsuit in CO'},
]

for case in test_cases:
    print(f'\n=== Testing {case["description"]} ===')
    category = categorize_preflop_hand(case['hand'])
    print(f'Hand category: {category}')
    
    game_state = {
        'my_player': {
            'stack': 1.0,
            'current_bet': 0.0,
            'hand': case['hand']
        },
        'pot_size': case['pot'],
        'max_bet_on_table': case['bet'] + 0.02,  # Slightly higher than bet_to_call
        'min_raise': 0.04,
        'big_blind': 0.02,
        'small_blind': 0.01,
        'can_check': False,
        'bet_to_call': case['bet'],
        'raise_amount_calculated': case['bet'] * 2.5,
        'num_opponents': 2,
        'num_limpers': 0,
        'is_bb': False,
        'position': case['position']
    }
    
    action, amount = make_preflop_decision(
        game_state['my_player'], 
        category, 
        case['position'], 
        case['bet'], 
        game_state['can_check'], 
        game_state['my_player']['stack'], 
        case['pot'], 
        game_state['num_opponents'], 
        game_state['small_blind'], 
        game_state['big_blind'], 
        game_state['my_player']['current_bet'], 
        game_state['max_bet_on_table'], 
        game_state['min_raise'],
        case['position'] == 'SB',  # is_sb
        case['position'] == 'BB',  # is_bb
        'fold', 'check', 'call', 'raise'  # action constants
    )
    print(f'Decision: {action}, Amount: {amount}')
