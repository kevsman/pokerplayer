"""
Configuration for the Poker Bot.
Loads settings from a JSON file (defaulting to config.json).
Provides default values for some settings if not found in the JSON file.
"""

import json
import os

# Default values that can be overridden by the config file
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_POKER_TABLE_WINDOW_TITLE = "PokerStars" # Example, adjust as needed

class Config:
    def __init__(self, config_path='config.json'):
        """
        Initializes the Config object by loading settings from a JSON file.

        Args:
            config_path (str): Path to the configuration JSON file.
        """
        self.config_path = config_path
        self.settings = {}
        self._load_config()

    def _load_config(self):
        """Loads configuration from the JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.settings = json.load(f)
            else:
                # Initialize with empty settings if config file doesn't exist,
                # relying on get_setting to provide defaults.
                self.settings = {}
                # Consider logging a warning or creating a default config file here
                # For now, we'll just proceed with defaults for required items.
                print(f"Warning: Config file not found at {self.config_path}. Using default settings where available.")

        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.config_path}. Using default settings where available.")
            self.settings = {} # Reset to empty on error to ensure defaults are used

        # Ensure essential default settings are available if not in file
        if 'LOG_LEVEL' not in self.settings:
            self.settings['LOG_LEVEL'] = DEFAULT_LOG_LEVEL
        if 'POKER_TABLE_WINDOW_TITLE' not in self.settings:
            self.settings['POKER_TABLE_WINDOW_TITLE'] = DEFAULT_POKER_TABLE_WINDOW_TITLE
        
        # For UI positions, they are expected to be loaded by UIController or be in the config.
        # If not, UIController should handle defaults or raise errors.
        # Example: self.settings.setdefault('POSITIONS', {})

    def get_setting(self, key, default=None):
        """
        Retrieves a setting value by key.

        Args:
            key (str): The key of the setting to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The value of the setting, or the default value if not found.
        """
        return self.settings.get(key, default)

    def __getattr__(self, name):
        """
        Allows accessing settings as attributes (e.g., config.LOG_LEVEL).
        """
        if name in self.settings:
            return self.settings[name]
        # Fallback for constants previously defined at module level, if desired,
        # or raise AttributeError if strict adherence to config file is preferred.
        if name == "LOG_LEVEL":
            return DEFAULT_LOG_LEVEL
        if name == "POKER_TABLE_WINDOW_TITLE":
            return DEFAULT_POKER_TABLE_WINDOW_TITLE
        
        # If the attribute is not found in settings or as a predefined default,
        # it might indicate a missing configuration or a typo.
        # Raising an AttributeError makes this explicit.
        raise AttributeError(f"\'{type(self).__name__}\' object has no attribute \'{name}\'. Check your config file or attribute name.")

# Example of how it might be used (for testing or direct script runs):
if __name__ == '__main__':
    # Create a dummy config.json for testing
    dummy_config_data = {
        "LOG_LEVEL": "DEBUG",
        "POKER_TABLE_WINDOW_TITLE": "My Poker Game",
        "DATABASE_SETTINGS": {
            "host": "localhost",
            "port": 5432
        },
        "POSITIONS": {
            "fold_button": {"x": 100, "y": 200}
        }
    }
    with open('config.json', 'w') as f:
        json.dump(dummy_config_data, f, indent=4)

    config = Config('config.json')
    print(f"Log Level: {config.LOG_LEVEL}") # Access via __getattr__
    print(f"Window Title: {config.get_setting('POKER_TABLE_WINDOW_TITLE')}") # Access via get_setting
    print(f"Database Host: {config.DATABASE_SETTINGS['host']}") # Access nested dict
    print(f"Fold button X: {config.POSITIONS['fold_button']['x']}")

    # Test missing key with default
    print(f"Missing Key (with default): {config.get_setting('MISSING_KEY', 'default_value')}")

    # Test accessing a non-existent attribute (should raise AttributeError)
    try:
        print(config.NON_EXISTENT_SETTING)
    except AttributeError as e:
        print(e)
    
    # Clean up dummy file
    os.remove('config.json')

# Original constants (can be removed or kept for reference, but Config class is primary)
# POKER_TABLE_WINDOW_TITLE = "PokerStars" 
# LOG_LEVEL = "INFO"
