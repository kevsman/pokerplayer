#!/usr/bin/env python3
"""
Quick strategy data inspector
"""
import json
import ast

def inspect_strategies():
    print('🔍 STRATEGY DATA INSPECTOR')
    print('=' * 40)
    
    try:
        with open('strategy_table.json', 'r') as f:
            string_keys_table = json.load(f)
        
        print(f'📊 Total strategies: {len(string_keys_table):,}')
        
        # Sample a few keys to understand format
        sample_keys = list(string_keys_table.keys())[:10]
        print('\n🎯 Sample strategy keys:')
        
        for i, key_str in enumerate(sample_keys[:5]):
            try:
                key = ast.literal_eval(key_str)
                strategy = string_keys_table[key_str]
                print(f'{i+1}. {key} -> {strategy}')
            except Exception as e:
                print(f'{i+1}. ERROR: {key_str} -> {e}')
        
        # Check what stages/buckets exist
        stages = set()
        hand_buckets = set()
        board_buckets = set()
        
        for key_str in list(string_keys_table.keys())[:1000]:  # Sample first 1000
            try:
                key = ast.literal_eval(key_str)
                if len(key) >= 3:
                    stages.add(str(key[0]))
                    hand_buckets.add(str(key[1]))
                    board_buckets.add(str(key[2]))
            except:
                continue
        
        print(f'\n📈 Data distribution (first 1000 keys):')
        print(f'Stages: {sorted(stages)}')
        print(f'Hand buckets (sample): {sorted(list(hand_buckets))[:20]}...')
        print(f'Board buckets (sample): {sorted(list(board_buckets))[:20]}...')
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    inspect_strategies()
