"""
Strategy lookup module for PokerBotV2.
Stores and retrieves precomputed strategies for abstracted game states.
"""
import json
import os

class StrategyLookup:
    def __init__(self, strategy_file='strategy_table.json'):
        self.strategy_file = strategy_file
        self.strategy_table = self._load_strategy_table()

    def _load_strategy_table(self):
        if not os.path.exists(self.strategy_file):
            return {}
        try:
            with open(self.strategy_file, 'r') as f:
                # Keys are stored as strings in JSON, so we need to convert them back to tuples
                string_keys_table = json.load(f)
                return {eval(k): v for k, v in string_keys_table.items()}
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_strategy_table(self):
        try:
            with open(self.strategy_file, 'w') as f:
                # JSON keys must be strings, so we convert tuples to strings
                string_keys_table = {str(k): v for k, v in self.strategy_table.items()}
                json.dump(string_keys_table, f, indent=4)
        except IOError:
            pass # Handle file write errors if necessary

    def get_strategy(self, stage, hand_bucket, board_bucket, actions):
        key = (stage, hand_bucket, board_bucket, tuple(sorted(actions)))
        return self.strategy_table.get(key, None)

    def add_strategy(self, stage, hand_bucket, board_bucket, actions, strategy):
        key = (stage, hand_bucket, board_bucket, tuple(sorted(actions)))
        self.strategy_table[key] = strategy
        self._save_strategy_table() # Save after adding a new strategy
