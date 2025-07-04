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
        """Loads the strategy table from the JSON file with corruption recovery."""
        if not os.path.exists(self.strategy_file):
            logger.error(f"Strategy file not found: {self.strategy_file}")
            return {}
        
        # Try to load main file
        for attempt_file in [self.strategy_file, self.strategy_file + ".backup"]:
            if not os.path.exists(attempt_file):
                continue
                
            try:
                logger.info(f"Attempting to load strategies from: {attempt_file}")
                with open(attempt_file, 'r') as f:
                    # Keys are stored as strings in JSON, so we convert them back to integers for lookup.
                    string_keys_table = json.load(f)
                    
                    # Validate the data structure
                    if not isinstance(string_keys_table, dict):
                        raise ValueError("Strategy file does not contain a valid dictionary")
                    
                    # Use a dictionary comprehension for efficient conversion with error handling
                    converted_table = {}
                    invalid_entries = 0
                    
                    for k, v in string_keys_table.items():
                        try:
                            hash_key = int(k)
                            if isinstance(v, dict) and all(isinstance(val, (int, float)) for val in v.values()):
                                converted_table[hash_key] = v
                            else:
                                invalid_entries += 1
                        except (ValueError, TypeError):
                            invalid_entries += 1
                    
                    if invalid_entries > 0:
                        logger.warning(f"Skipped {invalid_entries} invalid strategy entries")
                    
                    logger.info(f"Successfully loaded {len(converted_table)} valid strategies from {attempt_file}")
                    return converted_table
                    
            except (json.JSONDecodeError, IOError, ValueError) as e:
                logger.error(f"Error loading strategy file {attempt_file}: {e}")
                if attempt_file == self.strategy_file:
                    logger.info("Trying backup file...")
                    continue
        
        logger.error("All strategy file loading attempts failed")
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
