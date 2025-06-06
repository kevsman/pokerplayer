#!/usr/bin/env python3
"""Test script to verify Unicode logging works correctly."""

import logging
import sys
from poker_bot import PokerBot

def test_unicode_logging():
    """Test that Unicode characters in card symbols log correctly."""
    print("Testing Unicode logging with card symbols...")
    
    # Create a bot instance to test logging
    bot = PokerBot()
    
    # Test logging various Unicode card symbols
    test_cards = ['A♦', 'J♣', '8♥', '9♠', 'K♠', 'Q♦']
    
    bot.logger.info(f"Testing card symbols: {test_cards}")
    bot.logger.info(f"Hand: {test_cards[:2]}, Community: {test_cards[2:]}")
    
    # Test the specific scenario from the error
    bot.logger.info("My turn. Hand: ['A♦', 'J♣'], Rank: High Card, Stack: €1.98, Bet to call: 0.00")
    bot.logger.info("Pot: €0.05, Community Cards: ['8♥', '4♥', '9♠']")
    
    # Close the logger
    bot.close_logger()
    
    print("Unicode logging test completed successfully!")

if __name__ == "__main__":
    test_unicode_logging()
