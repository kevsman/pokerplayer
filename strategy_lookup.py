"""
Strategy lookup module for PokerBotV2.
Loads and retrieves pre-computed strategies from a strategy file using a direct hash lookup.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

class StrategyLookup:
    def __init__(self, strategy_file='strategy_table.json'):
        self.strategy_file = strategy_file
        logger.info(f"Initializing StrategyLookup with file: {strategy_file}")
        self.strategy_table = self._load_strategy_table()
        
        if self.strategy_table:
            logger.info(f"✅ Loaded {len(self.strategy_table)} strategies from file.")
        else:
            logger.warning(f"⚠️ Strategy file {self.strategy_file} is empty or could not be loaded.")

    def _load_strategy_table(self):
        """Loads the strategy table from the JSON file, converting keys to integers."""
        if not os.path.exists(self.strategy_file):
            logger.error(f"Strategy file not found: {self.strategy_file}")
            return {}
        try:
            with open(self.strategy_file, 'r') as f:
                # Keys are stored as strings in JSON, so we convert them back to integers for lookup.
                string_keys_table = json.load(f)
                # Use a dictionary comprehension for efficient conversion.
                return {int(k): v for k, v in string_keys_table.items()}
        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.error(f"Error loading or parsing strategy file {self.strategy_file}: {e}")
            return {}

    def get_strategy_by_hash(self, info_hash: int):
        """
        Retrieves a strategy directly using the information state hash.
        
        Args:
            info_hash (int): The hash representing the current game state.
            
        Returns:
            dict: The strategy dictionary if found, otherwise None.
        """
        return self.strategy_table.get(info_hash)
