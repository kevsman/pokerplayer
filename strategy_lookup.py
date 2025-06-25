"""
Strategy lookup module for PokerBotV2.
Stores and retrieves precomputed strategies for abstracted game states.
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
        logger.info(f"Loaded {len(self.strategy_table)} strategies from file")

    def _load_strategy_table(self):
        if not os.path.exists(self.strategy_file):
            logger.info(f"Strategy file {self.strategy_file} does not exist, starting with empty table")
            return {}
        try:
            import ast
            with open(self.strategy_file, 'r') as f:
                # Keys are stored as strings in JSON, so we need to convert them back to tuples
                string_keys_table = json.load(f)
                result = {ast.literal_eval(k): v for k, v in string_keys_table.items()}
                logger.info(f"Successfully loaded {len(result)} strategies from {self.strategy_file}")
                return result
        except (json.JSONDecodeError, IOError, ValueError, SyntaxError) as e:
            logger.error(f"Error loading strategy file {self.strategy_file}: {e}")
            return {}

    def _save_strategy_table(self):
        logger.info(f"Saving {len(self.strategy_table)} strategies to {self.strategy_file}")
        try:
            with open(self.strategy_file, 'w') as f:
                # JSON keys must be strings, so we convert tuples to strings
                string_keys_table = {str(k): v for k, v in self.strategy_table.items()}
                json.dump(string_keys_table, f, indent=4)
            logger.info(f"Successfully saved strategies to {self.strategy_file}")
        except IOError as e:
            logger.error(f"Error saving strategy file {self.strategy_file}: {e}")
            pass # Handle file write errors if necessary

    def get_strategy(self, stage, hand_bucket, board_bucket, actions):
        key = (stage, hand_bucket, board_bucket, tuple(sorted(actions)))
        return self.strategy_table.get(key, None)

    def add_strategy(self, stage, hand_bucket, board_bucket, actions, strategy):
        key = (stage, hand_bucket, board_bucket, tuple(sorted(actions)))
        self.strategy_table[key] = strategy
        logger.debug(f"Added strategy for key: {key}")
        # Don't save after every addition - save only when explicitly called

    def update_strategy(self, stage, hand_bucket, board_bucket, actions, strategy):
        """Update strategy - alias for add_strategy for compatibility"""
        logger.debug(f"update_strategy called: stage={stage}, hand_bucket={hand_bucket}, board_bucket={board_bucket}, actions={actions}")
        self.add_strategy(stage, hand_bucket, board_bucket, actions, strategy)

    def save_strategies(self):
        """Save all strategies to file"""
        logger.info(f"save_strategies called - saving {len(self.strategy_table)} strategies")
        self._save_strategy_table()
