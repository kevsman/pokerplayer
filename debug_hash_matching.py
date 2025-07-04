#!/usr/bin/env python3
"""
Debug script to compare hash generation between trainer and bot
"""
import numpy as np
import cupy as cp

def bot_hash_generation(street, turn_index, max_bet, effective_pot, num_active, avg_bet):
    """Exact copy of the bot's hash generation logic"""
    # EXACT MATCH to poker_bot_v2.py hash generation
    street_component = street * 10000000000
    player_component = turn_index * 1000000000
    maxbet_component = int(round(float(max_bet), 2) * 100) * 100000
    pot_component = int(round(float(effective_pot), 2) * 100) * 10
    active_component = num_active * 1000000
    avgbet_component = int(round(float(avg_bet), 2) * 100)
    
    # Enhanced hash combination matching the trainer
    combined_hash = (street_component + player_component + maxbet_component + 
                    pot_component + active_component + avgbet_component)
    
    # Apply the same enhanced mixing as the trainer
    combined_hash = combined_hash * 2654435761  # Large prime
    combined_hash = combined_hash ^ (combined_hash >> 16)  # XOR folding
    combined_hash = combined_hash * 1664525  # Another prime
    combined_hash = combined_hash ^ (combined_hash >> 24)  # More folding
    combined_hash = combined_hash & 0x7FFFFFFFFFFFFFFF  # Ensure positive
    
    return combined_hash

def trainer_hash_generation(street, current_player, max_bet, effective_pot, num_active, avg_bet):
    """Exact copy of the trainer's hash generation logic"""
    # EXACT MATCH to gpu_cfr_trainer.py hash generation
    street_component = street * 10000000000
    player_component = current_player * 1000000000
    maxbet_component = int(round(float(max_bet), 2) * 100) * 100000
    pot_component = int(round(float(effective_pot), 2) * 100) * 10
    active_component = num_active * 1000000
    avgbet_component = int(round(float(avg_bet), 2) * 100)
    
    # Enhanced hash combination matching the bot exactly
    combined_hash = (street_component + player_component + maxbet_component + 
                    pot_component + active_component + avgbet_component)
    
    # Apply the same enhanced mixing as the bot
    combined_hash = combined_hash * 2654435761  # Large prime
    combined_hash = combined_hash ^ (combined_hash >> 16)  # XOR folding
    combined_hash = combined_hash * 1664525  # Another prime
    combined_hash = combined_hash ^ (combined_hash >> 24)  # More folding
    combined_hash = combined_hash & 0x7FFFFFFFFFFFFFFF  # Ensure positive
    
    return combined_hash

if __name__ == '__main__':
    # Test the same scenario as the bot test
    # Bot test state: (0, 0, 0.02, 0.06, 2, 0.01)
    street = 0
    turn_index = 0  # Bot's turn index
    max_bet = 0.02
    effective_pot = 0.06
    num_active = 2
    avg_bet = 0.01
    
    print("=== HASH DEBUGGING ===")
    print(f"Test scenario: street={street}, turn_index={turn_index}, max_bet={max_bet}, effective_pot={effective_pot}, num_active={num_active}, avg_bet={avg_bet}")
    
    bot_hash = bot_hash_generation(street, turn_index, max_bet, effective_pot, num_active, avg_bet)
    trainer_hash = trainer_hash_generation(street, turn_index, max_bet, effective_pot, num_active, avg_bet)
    
    print(f"Bot hash:     {bot_hash}")
    print(f"Trainer hash: {trainer_hash}")
    print(f"Match: {bot_hash == trainer_hash}")
    
    if bot_hash != trainer_hash:
        print("\n=== COMPONENT BREAKDOWN ===")
        # Bot components
        street_component_bot = street * 10000000000
        player_component_bot = turn_index * 1000000000
        maxbet_component_bot = int(round(float(max_bet), 2) * 100) * 100000
        pot_component_bot = int(round(float(effective_pot), 2) * 100) * 10
        active_component_bot = num_active * 1000000
        avgbet_component_bot = int(round(float(avg_bet), 2) * 100)
        
        # Trainer components (same variables)
        street_component_trainer = street * 10000000000
        player_component_trainer = turn_index * 1000000000
        maxbet_component_trainer = int(round(float(max_bet), 2) * 100) * 100000
        pot_component_trainer = int(round(float(effective_pot), 2) * 100) * 10
        active_component_trainer = num_active * 1000000
        avgbet_component_trainer = int(round(float(avg_bet), 2) * 100)
        
        print(f"Street component - Bot: {street_component_bot}, Trainer: {street_component_trainer}, Match: {street_component_bot == street_component_trainer}")
        print(f"Player component - Bot: {player_component_bot}, Trainer: {player_component_trainer}, Match: {player_component_bot == player_component_trainer}")
        print(f"MaxBet component - Bot: {maxbet_component_bot}, Trainer: {maxbet_component_trainer}, Match: {maxbet_component_bot == maxbet_component_trainer}")
        print(f"Pot component - Bot: {pot_component_bot}, Trainer: {pot_component_trainer}, Match: {pot_component_bot == pot_component_trainer}")
        print(f"Active component - Bot: {active_component_bot}, Trainer: {active_component_trainer}, Match: {active_component_bot == active_component_trainer}")
        print(f"AvgBet component - Bot: {avgbet_component_bot}, Trainer: {avgbet_component_trainer}, Match: {avgbet_component_bot == avgbet_component_trainer}")
    
    # Test a few different scenarios that might appear during training
    print("\n=== TESTING VARIOUS SCENARIOS ===")
    test_scenarios = [
        (0, 0, 0.02, 0.06, 2, 0.01),  # Current test scenario
        (0, 1, 0.04, 0.08, 2, 0.02),  # Big blind with a call
        (0, 0, 0.08, 0.14, 2, 0.04),  # Small blind after raise
        (1, 0, 0.0, 0.14, 2, 0.0),    # Flop, no bets yet
        (1, 1, 0.02, 0.16, 2, 0.01),  # Flop with bet
    ]
    
    for i, (st, turn, max_b, eff_pot, num_act, avg_b) in enumerate(test_scenarios):
        bot_h = bot_hash_generation(st, turn, max_b, eff_pot, num_act, avg_b)
        trainer_h = trainer_hash_generation(st, turn, max_b, eff_pot, num_act, avg_b)
        print(f"Scenario {i+1}: {(st, turn, max_b, eff_pot, num_act, avg_b)} -> Bot: {bot_h}, Trainer: {trainer_h}, Match: {bot_h == trainer_h}")
    
    print("\n=== STRATEGY TABLE CHECK ===")
    # Check if any of these hashes exist in the strategy table
    try:
        with open('strategy_table.json', 'r') as f:
            import json
            strategy_data = json.load(f)
            strategy_hashes = set(map(int, strategy_data.keys()))
            
            print(f"Strategy table contains {len(strategy_hashes)} unique hashes")
            print(f"Sample hashes from strategy table: {list(strategy_hashes)[:10]}")
            
            for i, (st, turn, max_b, eff_pot, num_act, avg_b) in enumerate(test_scenarios):
                bot_h = bot_hash_generation(st, turn, max_b, eff_pot, num_act, avg_b)
                found = bot_h in strategy_hashes
                print(f"Scenario {i+1} hash {bot_h} found in strategy table: {found}")
    except Exception as e:
        print(f"Could not check strategy table: {e}")
