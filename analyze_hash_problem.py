#!/usr/bin/env python3
"""
Analyze the problematic hash scenario to understand why fuzzy matching failed.
"""

def analyze_hash_scenario():
    """Analyze the hash components of the problematic scenario."""
    
    # The bot's actual situation
    target_hash = 4929814766040804927
    target_state = (3, 4, 0.58, 1.94, 6, 0.1)  # (street, turn_index, max_bet, effective_pot, num_active, avg_bet)
    
    # The fuzzy-matched strategy hash  
    matched_hash = 7848782567973857233
    
    print("🔍 Hash Scenario Analysis")
    print("=" * 60)
    print(f"Target Hash: {target_hash}")
    print(f"Target State: {target_state}")
    print(f"- Street: {target_state[0]} (River)")
    print(f"- Turn Index: {target_state[1]} (5th to act)")
    print(f"- Max Bet: ${target_state[2]:.2f}")
    print(f"- Effective Pot: ${target_state[3]:.2f}")
    print(f"- Active Players: {target_state[4]}")
    print(f"- Average Bet: ${target_state[5]:.2f}")
    print()
    print(f"Matched Hash: {matched_hash}")
    print("Matched Strategy: ALL-IN 98.39% of the time!")
    print()
    print("🚨 PROBLEM ANALYSIS:")
    print("- Bot had weak hand (3♥, 10♥) on river")
    print("- Board had paired aces (Q♦, 7♥, A♣, A♦, 9♣)")
    print("- Fuzzy matching found aggressive strategy from different scenario")
    print("- 67.2% similarity threshold allowed inappropriate match")
    print()
    print("🛠️ SOLUTIONS:")
    print("1. Increase fuzzy matching similarity threshold")
    print("2. Add hand strength validation before applying strategy")
    print("3. Implement scenario-specific fallbacks")
    print("4. Add sanity checks for extreme strategies on river")

def reverse_engineer_hash(street, turn_index, max_bet, effective_pot, num_active, avg_bet):
    """Reverse engineer hash from components to understand what scenario the matched hash represents."""
    
    street_component = street * 10000000000
    player_component = turn_index * 1000000000
    maxbet_component = int(round(float(max_bet), 2) * 100) * 100000
    pot_component = int(round(float(effective_pot), 2) * 100) * 10
    active_component = num_active * 1000000
    avgbet_component = int(round(float(avg_bet), 2) * 100)
    
    combined_hash = (street_component + player_component + maxbet_component + 
                    pot_component + active_component + avgbet_component)
    
    # Apply the same enhanced mixing
    combined_hash = combined_hash * 2654435761
    combined_hash = combined_hash ^ (combined_hash >> 16)
    combined_hash = combined_hash * 1664525
    combined_hash = combined_hash ^ (combined_hash >> 24)
    combined_hash = combined_hash & 0x7FFFFFFFFFFFFFFF
    
    return combined_hash

if __name__ == "__main__":
    analyze_hash_scenario()
    
    print("\n🔍 Trying to reverse engineer the matched hash scenario...")
    print("=" * 60)
    
    # Try different scenarios that might generate the matched hash
    matched_hash = 7848782567973857233
    
    scenarios_to_test = [
        # Different streets, positions, and pot sizes
        (3, 0, 2.0, 4.0, 2, 1.0),   # River, first to act, big pot
        (3, 1, 1.0, 3.0, 2, 0.5),   # River, second to act
        (2, 0, 1.5, 2.5, 3, 0.5),   # Turn, first to act
        (1, 2, 0.8, 1.6, 4, 0.2),   # Flop, third to act
        (0, 1, 0.04, 0.12, 6, 0.02), # Preflop scenario
    ]
    
    print("Testing scenarios that might match the aggressive strategy hash:")
    for i, scenario in enumerate(scenarios_to_test, 1):
        test_hash = reverse_engineer_hash(*scenario)
        print(f"{i}. State {scenario} -> Hash: {test_hash}")
        if test_hash == matched_hash:
            print(f"   🎯 MATCH FOUND! This aggressive strategy was trained for: {scenario}")
            break
    else:
        print("❌ No exact match found in test scenarios")
