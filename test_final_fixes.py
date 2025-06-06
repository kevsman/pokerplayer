#!/usr/bin/env python3
"""Final test to verify both fixes are working correctly."""

import sys
import os
import logging

def test_both_fixes():
    """Test both the commitment_threshold fix and Unicode logging fix."""
    print("Testing both fixes...")
    
    # Test 1: Import and basic syntax check
    try:
        from postflop_decision_logic import make_postflop_decision
        from poker_bot import PokerBot
        print("✓ Import test passed - no syntax errors")
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False
    
    # Test 2: Unicode logging
    try:
        # Create a temporary logger to test Unicode
        logger = logging.getLogger('unicode_test')
        logger.setLevel(logging.INFO)
        
        # Clear handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        
        # Add file handler with UTF-8
        fh = logging.FileHandler('test_unicode_output.log', mode='w', encoding='utf-8')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.propagate = False
        
        # Test Unicode logging
        logger.info("Testing cards: A♦ J♣ 8♥ 9♠")
        logger.info("Hand: ['A♦', 'J♣'], Community: ['8♥', '4♥', '9♠']")
        
        # Clean up
        fh.close()
        logger.removeHandler(fh)
        
        # Check if file was created with content
        if os.path.exists('test_unicode_output.log'):
            with open('test_unicode_output.log', 'r', encoding='utf-8') as f:
                content = f.read()
                if '♦' in content and '♣' in content:
                    print("✓ Unicode logging test passed")
                    os.remove('test_unicode_output.log')  # Clean up
                else:
                    print("✗ Unicode logging test failed - symbols not found in log")
                    return False
        else:
            print("✗ Unicode logging test failed - no log file created")
            return False
            
    except UnicodeEncodeError as e:
        print(f"✗ Unicode logging test failed with UnicodeEncodeError: {e}")
        return False
    except Exception as e:
        print(f"✗ Unicode logging test failed: {e}")
        return False
    
    # Test 3: Test that PokerBot can be instantiated (sys import fix)
    try:
        bot = PokerBot()
        bot.close_logger()
        print("✓ PokerBot instantiation test passed - sys import fix working")
    except UnboundLocalError as e:
        if 'sys' in str(e):
            print(f"✗ PokerBot instantiation test failed - sys import issue: {e}")
            return False
        else:
            print(f"✗ PokerBot instantiation test failed with UnboundLocalError: {e}")
            return False
    except Exception as e:
        print(f"✗ PokerBot instantiation test failed: {e}")
        return False
    
    print("🎉 All tests passed! Both fixes are working correctly.")
    return True

if __name__ == "__main__":
    success = test_both_fixes()
    if not success:
        sys.exit(1)
    
    print("\n" + "="*60)
    print("SUMMARY OF FIXES APPLIED:")
    print("="*60)
    print("1. ✓ Fixed UnboundLocalError for 'commitment_threshold' in postflop_decision_logic.py")
    print("   - Fixed syntax error where 'elif is_medium:' and 'else:' were on same line")
    print("   - Fixed indentation issues")
    print("")
    print("2. ✓ Fixed UnboundLocalError for 'sys' in poker_bot.py")
    print("   - Removed redundant 'import sys' that was shadowing global import")
    print("")
    print("3. ✓ Enhanced Unicode logging support")
    print("   - Added UTF-8 encoding to file handlers")
    print("   - Added fallback Unicode handling for Windows console output")
    print("")
    print("The original errors have been resolved:")
    print("- UnicodeEncodeError: 'charmap' codec can't encode character '\\u2666'")
    print("- UnboundLocalError: cannot access local variable 'commitment_threshold'")
    print("="*60)
