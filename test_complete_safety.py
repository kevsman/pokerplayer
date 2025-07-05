#!/usr/bin/env python3
"""
Test the complete safety system: SafeStrategyLookup + Monte Carlo with fallback
"""
import sys
import logging
from poker_bot_v2 import PokerBotV2

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:%(name)s:%(message)s'
)

def test_safety_scenarios():
    """Test multiple scenarios to ensure the bot is safe and robust"""
    bot = PokerBotV2()
    
    scenarios = [
        # Strong hands - should never fold on safe boards
        {
            'name': 'KK on dry board',
            'hole_cards': ['K♠', 'K♥'],
            'community_cards': ['8♠', '5♥', '4♣'],
            'stage': 'flop',
            'actions': ['fold', 'call', 'raise'],
            'pot_size': 0.28,
            'expected': 'Should rarely fold KK'
        },
        {
            'name': 'AA on safe board',
            'hole_cards': ['A♠', 'A♥'],
            'community_cards': ['9♠', '6♥', '2♣'],
            'stage': 'flop',
            'actions': ['fold', 'call', 'raise'],
            'pot_size': 0.30,
            'expected': 'Should almost never fold AA'
        },
        # Weak hands - should fold frequently 
        {
            'name': 'Trash on river',
            'hole_cards': ['7♠', '2♥'],
            'community_cards': ['K♠', 'Q♥', 'J♣', '9♠', '5♦'],
            'stage': 'river',
            'actions': ['fold', 'call'],
            'pot_size': 1.50,
            'expected': 'Should fold trash frequently'
        },
        {
            'name': 'Weak ace on dangerous board',
            'hole_cards': ['A♠', '3♥'],
            'community_cards': ['K♠', 'Q♥', 'J♣'],
            'stage': 'flop',
            'actions': ['fold', 'call', 'raise'],
            'pot_size': 0.45,
            'expected': 'Should be cautious with weak ace'
        }
    ]
    
    print("🧪 Testing Complete Safety System")
    print("=" * 60)
    
    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print(f"Hand: {scenario['hole_cards']}")
        print(f"Board: {scenario['community_cards']}")
        print(f"Expected: {scenario['expected']}")
        
        try:
            strategy = bot.get_decision(
                hole_cards=scenario['hole_cards'],
                community_cards=scenario['community_cards'],
                stage=scenario['stage'],
                actions=scenario['actions'],
                pot_size=scenario['pot_size'],
                num_opponents=3
            )
            
            print(f"Strategy: {strategy}")
            
            # Analyze strategy safety
            fold_prob = strategy.get('fold', 0.0)
            raise_prob = strategy.get('raise', 0.0) + strategy.get('bet', 0.0)
            
            if 'KK' in scenario['name'] or 'AA' in scenario['name']:
                if fold_prob > 0.15:  # Should rarely fold strong hands
                    print(f"⚠️  WARNING: High fold probability ({fold_prob:.1%}) for strong hand!")
                else:
                    print(f"✅ Good: Low fold probability ({fold_prob:.1%}) for strong hand")
                    
            elif 'Trash' in scenario['name'] or 'Weak' in scenario['name']:
                if fold_prob < 0.30:  # Should often fold weak hands
                    print(f"⚠️  WARNING: Low fold probability ({fold_prob:.1%}) for weak hand!")
                else:
                    print(f"✅ Good: High fold probability ({fold_prob:.1%}) for weak hand")
                    
        except Exception as e:
            print(f"❌ Error in scenario: {e}")
            
    print("\n" + "=" * 60)
    print("🏁 Safety testing complete!")

if __name__ == "__main__":
    test_safety_scenarios()
