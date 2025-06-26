#!/usr/bin/env python3
import json
import ast

print('📊 EXAMINING STRATEGY DATA FORMAT')
print('=' * 50)

try:
    with open('strategy_table.json', 'r') as f:
        string_keys_table = json.load(f)
    
    print(f'Total strategies loaded: {len(string_keys_table):,}')
    
    # Examine first few keys
    sample_keys = list(string_keys_table.keys())[:10]
    print('\n🔍 SAMPLE STRATEGY KEYS:')
    
    for i, key_str in enumerate(sample_keys):
        try:
            key = ast.literal_eval(key_str)
            strategy = string_keys_table[key_str]
            print(f'{i+1:2d}. Raw key: {key_str}')
            print(f'    Parsed: {key}')
            print(f'    Strategy: {strategy}')
            print()
        except Exception as e:
            print(f'Error parsing key {key_str}: {e}')
        
        if i >= 4:  # Show first 5
            break
    
    # Try to find keys that might match our test cases
    print('\n🎯 SEARCHING FOR MATCHING PATTERNS:')
    search_patterns = [
        ('0', '0', '0'),
        ('0', '1', '0'), 
        ('0', '5', '0'),
        ('0', '10', '0'),
    ]
    
    for pattern in search_patterns:
        found = False
        for key_str in sample_keys[:100]:  # Check first 100
            try:
                key = ast.literal_eval(key_str)
                if len(key) >= 3 and str(key[0]) == pattern[0] and str(key[1]) == pattern[1] and str(key[2]) == pattern[2]:
                    print(f'✅ Found match for {pattern}: {key}')
                    found = True
                    break
            except:
                continue
        if not found:
            print(f'❌ No exact match found for {pattern}')

except Exception as e:
    print(f'Error loading strategy file: {e}')
