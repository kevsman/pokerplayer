#!/usr/bin/env python3
import sys
print("=== Testing Correct Card Format ===", file=sys.stderr)
sys.stderr.flush()
try:
    from equity_calculator import EquityCalculator
    
    calculator = EquityCalculator()
    
    # Test with tuple format (current issue)
    print("Testing tuple format [(A, SPADES), (A, HEARTS)]:", file=sys.stderr)
    try:
        result1 = calculator.calculate_win_probability([('A', 'SPADES'), ('A', 'HEARTS')], [])
        print(f"  Result: {result1}", file=sys.stderr)
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
    
    # Test with correct format
    print("Testing correct format ['As', 'Ah']:", file=sys.stderr)
    try:
        result2 = calculator.calculate_win_probability(['As', 'Ah'], [])
        print(f"  Result: {result2}", file=sys.stderr)
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
    
    # Test with board cards
    print("Testing with board cards:", file=sys.stderr)
    try:
        result3 = calculator.calculate_win_probability(['As', 'Ah'], ['2c', '7h', 'Qd'])
        print(f"  AA on 2-7-Q board: {result3}", file=sys.stderr)
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
    
    print("Testing weak hand:", file=sys.stderr)
    try:
        result4 = calculator.calculate_win_probability(['8s', '7h'], ['Ac', 'Kh', 'Qd'])
        print(f"  87o on A-K-Q board: {result4}", file=sys.stderr)
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        
except Exception as e:
    import traceback
    print(f"Error: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.stderr.flush()
print("=== Card Format Test Complete ===", file=sys.stderr)
sys.stderr.flush()
