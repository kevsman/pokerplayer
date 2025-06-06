#!/usr/bin/env python3
"""Simple test for Unicode logging without running full bot."""

import logging
import sys
import io

def test_unicode_simple():
    """Test Unicode logging configuration."""
    # Set up logging similar to poker_bot.py
    logger = logging.getLogger('test_unicode')
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    
    # Create file handler with UTF-8 encoding
    fh = logging.FileHandler('test_unicode.log', mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    # Create console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    # Set encoding for StreamHandler to handle Unicode on Windows
    if hasattr(ch, 'stream') and hasattr(ch.stream, 'reconfigure'):
        try:
            ch.stream.reconfigure(encoding='utf-8')
        except Exception:
            # Fallback: create a new StreamHandler with proper encoding
            if sys.platform.startswith('win'):
                # For Windows, wrap stdout to handle Unicode properly
                utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                ch = logging.StreamHandler(utf8_stdout)
                ch.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.propagate = False
    
    # Test logging with Unicode characters
    print("Testing Unicode logging...")
    
    try:
        logger.info("Testing card symbols: A♦ J♣ 8♥ 9♠")
        logger.info("Hand: ['A♦', 'J♣'], Community: ['8♥', '4♥', '9♠']")
        logger.info("Stack: €1.98, Pot: €0.05")
        print("✓ Unicode logging test PASSED!")
        
    except UnicodeEncodeError as e:
        print(f"✗ Unicode logging test FAILED: {e}")
        return False
    
    finally:
        # Clean up
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
    
    return True

if __name__ == "__main__":
    success = test_unicode_simple()
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
        sys.exit(1)
