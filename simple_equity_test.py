#!/usr/bin/env python3
"""
Simple equity calculator test to verify the basic functionality works
"""

import random
from hand_evaluator import HandEvaluator

def simple_equity_calculation(hero_cards, community_cards, num_simulations=100):
    """
    Simple equity calculation without complex error handling
    """
    print(f"Testing: {hero_cards} vs random opponent")
    print(f"Community: {community_cards}")
    
    hand_evaluator = HandEvaluator()
    
    # Generate full deck
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['♠', '♥', '♦', '♣']
    all_cards = [rank + suit for rank in ranks for suit in suits]
    
    # Remove known cards
    known_cards = hero_cards + community_cards
    available_cards = [c for c in all_cards if c not in known_cards]
    
    print(f"Available cards for simulation: {len(available_cards)}")
    
    wins = 0
    ties = 0
    successful_sims = 0
    
    for i in range(num_simulations):
        try:
            # Need 2 cards for opponent + remaining board cards
            cards_needed_for_board = max(0, 5 - len(community_cards))
            total_cards_needed = 2 + cards_needed_for_board
            
            if len(available_cards) < total_cards_needed:
                print(f"Not enough cards available: {len(available_cards)} < {total_cards_needed}")
                continue
            
            # Deal opponent cards
            sim_deck = available_cards.copy()
            opponent_cards = random.sample(sim_deck, 2)
            
            # Remove opponent cards from deck
            for card in opponent_cards:
                sim_deck.remove(card)
            
            # Deal additional board cards if needed
            additional_board = []
            if cards_needed_for_board > 0:
                additional_board = random.sample(sim_deck, cards_needed_for_board)
            
            # Complete board
            final_board = community_cards + additional_board
            
            # Evaluate both hands
            hero_eval = hand_evaluator.evaluate_hand(hero_cards, final_board)
            opponent_eval = hand_evaluator.evaluate_hand(opponent_cards, final_board)
            
            # Compare hands
            hero_rank = hero_eval.get('rank_value', 0)
            opponent_rank = opponent_eval.get('rank_value', 0)
            
            if hero_rank > opponent_rank:
                wins += 1
            elif hero_rank == opponent_rank:
                # Compare tie breakers
                hero_tb = hero_eval.get('tie_breakers', [])
                opponent_tb = opponent_eval.get('tie_breakers', [])
                comparison = hand_evaluator._compare_tie_breakers(hero_tb, opponent_tb)
                if comparison > 0:
                    wins += 1
                elif comparison == 0:
                    ties += 1
            
            successful_sims += 1
            
            if i < 3:  # Debug first few simulations
                print(f"Sim {i}: Hero={hero_eval.get('description')}, Opp={opponent_eval.get('description')}")
                
        except Exception as e:
            print(f"Error in simulation {i}: {e}")
            continue
    
    if successful_sims == 0:
        print("No successful simulations!")
        return 0.0
    
    win_rate = wins / successful_sims
    tie_rate = ties / successful_sims
    equity = win_rate + (tie_rate / 2)
    
    print(f"Results: {wins} wins, {ties} ties out of {successful_sims} simulations")
    print(f"Win rate: {win_rate:.3f} ({win_rate*100:.1f}%)")
    print(f"Equity: {equity:.3f} ({equity*100:.1f}%)")
    
    return equity

if __name__ == "__main__":
    # Test with pocket aces
    print("=== Testing Pocket Aces ===")
    simple_equity_calculation(['A♠', 'A♥'], [], 100)
    
    print("\n=== Testing K8 offsuit ===")
    simple_equity_calculation(['K♠', '8♥'], ['A♠', '2♥', '3♦'], 100)
