'''
Handles mouse control, screen capture, and other UI interactions.
'''
import pyautogui
import pyperclip
import time
import json
import random # Added for click randomization

CONFIG_FILE = "config.json"
DEFAULT_DELAYS = {
    "main_loop_general_delay": 0.5, # seconds
    "after_action_delay": 1.5, # seconds
    "short_pause": 0.25, # seconds
    "medium_pause": 0.5, # seconds
    "long_pause": 1.0 # seconds
}

class UIController:
    def __init__(self, logger=None, config_object=None): # Modified to accept logger and config
        self.logger = logger
        self.positions = {}
        self.delays = DEFAULT_DELAYS.copy() # Initialize with defaults
        self.config = {} # Initialize config dictionary
        
        # If a config_object is passed (e.g. from PokerBot), use it
        if config_object:
            # Assuming config_object has a method to get all settings or is a dict
            if hasattr(config_object, 'get_all_settings'):
                self.config = config_object.get_all_settings()
            elif isinstance(config_object, dict):
                self.config = config_object
            else:
                self.log_warning("Config object passed to UIController is not of expected type, loading from file.")
                self.load_config_from_file() # Fallback to loading from file
            
            # Extract positions and delays from the passed config if available
            self.positions = self.config.get("positions", {})
            loaded_delays = self.config.get("delays", {})
            for key, value in loaded_delays.items():
                if key in self.delays:
                    self.delays[key] = value
        else:
            # Fallback to loading from file if no config_object is provided
            self.load_config_from_file()

    def log_info(self, message):
        if self.logger:
            self.logger.info(message)
        else:
            print(f"INFO: {message}")

    def log_warning(self, message):
        if self.logger:
            self.logger.warning(message)
        else:
            print(f"WARNING: {message}")

    def log_error(self, message):
        if self.logger:
            self.logger.error(message)
        else:
            print(f"ERROR: {message}")

    def load_config_from_file(self): # Renamed from load_config to avoid confusion
        try:
            with open(CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                # self.config = config_data.copy() # Store the full config - This is now handled by the main config object if passed
                # If self.config is still empty (meaning no config_object was passed or it was minimal)
                if not self.config:
                    self.config = config_data.copy()

                self.positions = config_data.get("positions", self.positions if self.positions else {}) # Prioritize already set positions
                
                # Load delays, merging with defaults to ensure all keys are present
                loaded_delays = config_data.get("delays", {})
                for key, value in loaded_delays.items():
                    if key in self.delays: # Only update if key is a recognized delay setting
                        self.delays[key] = value
        except FileNotFoundError:
            self.log_warning(f"{CONFIG_FILE} not found. Using default positions and delays. Calibration needed.")
            # self.config = {} # Keep potentially passed config
            self.positions = self.positions if self.positions else {}
            self.delays = DEFAULT_DELAYS.copy()
        except json.JSONDecodeError:
            self.log_error(f"Could not decode {CONFIG_FILE}. Using default positions and delays.")
            # self.config = {} # Keep potentially passed config
            self.positions = self.positions if self.positions else {}
            self.delays = DEFAULT_DELAYS.copy()

    def save_config(self):
        # Start with existing config to preserve all settings
        # If self.config was populated by a passed config_object, we update that structure
        # Otherwise, we build it from scratch or from file-loaded data.
        config_data_to_save = self.config.copy() if self.config else {}
        
        # Update with current positions and delays
        config_data_to_save["positions"] = self.positions
        config_data_to_save["delays"] = self.delays
        
        # Ensure auto_search has default values if not present
        if "auto_search" not in config_data_to_save:
            config_data_to_save["auto_search"] = {
                "enabled": True,
                "step_size": 5,
                "max_attempts": 60
            }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data_to_save, f, indent=4)
            self.log_info(f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            self.log_error(f"Error saving config to {CONFIG_FILE}: {e}")
        
        # Update our internal config to match what was saved, especially if it was minimal before
        self.config = config_data_to_save

    def calibrate_position(self, name):
        input(f"Move mouse to '{name}' and press Enter...")
        x, y = pyautogui.position()
        if "positions" not in self.positions: # Ensure positions dict exists
            self.positions["positions"] = {}
        self.positions[name] = {"x": x, "y": y}
        print(f"Position '{name}' calibrated at ({x}, {y})")
        self.save_config() # Save entire config (positions and delays)

    def calibrate_all(self):
        print("Starting UI calibration process...")
        
        # Enhanced calibration: ask for both HTML capture point and starting search point
        self.calibrate_position("html_capture_point") # Point to click for copying HTML
        
        # Ask for starting search point for automatic recalibration
        print("\nFor automatic recalibration when HTML capture fails:")
        print("This should be a point above the HTML capture point where we can start searching downward.")
        self.calibrate_position("html_search_start_point")
        
        self.calibrate_position("fold_button")
        self.calibrate_position("check_call_button") # Assumes check and call are the same button
        self.calibrate_position("all_in_button") # Added for the all-in scenario
        self.calibrate_position("raise_button") # This might be the button that opens the raise input
        self.calibrate_position("raise_input_field") # The actual input field for the amount
        self.calibrate_position("confirm_raise_button") # The button to confirm the raise after typing amount
        print("Calibration complete. Positions saved.")
        # Optionally, prompt for delay configuration or inform about defaults
        print(f"Current delays (loaded from config or default): {self.delays}")
        print(f"You can manually edit '{CONFIG_FILE}' to change delay values if needed.")

    def auto_search_for_valid_html_capture_point(self, step_size=None, max_attempts=None):
        """
        Automatically search for a valid HTML capture point by moving downward from the starting search point.
        
        Args:
            step_size (int): Number of pixels to move down in each attempt (uses config default if None)
            max_attempts (int): Maximum number of attempts before giving up (uses config default if None)
            
        Returns:
            bool: True if a valid capture point was found and saved, False otherwise
        """
        # Use config values if parameters not provided
        if step_size is None:
            step_size = self.config.get('auto_search', {}).get('step_size', 5)
        if max_attempts is None:
            max_attempts = self.config.get('auto_search', {}).get('max_attempts', 60)
        if "html_search_start_point" not in self.positions:
            print("Error: Starting search point not calibrated. Cannot perform automatic search.")
            return False
        
        start_pos = self.positions["html_search_start_point"]
        start_x, start_y = start_pos["x"], start_pos["y"]
        
        print(f"Starting automatic search for valid HTML capture point from ({start_x}, {start_y})")
        
        # Import html_parser to test HTML validity
        try:
            from html_parser import PokerPageParser
            parser = PokerPageParser(logger=self.logger, config=self.config) # Pass logger and config
        except ImportError:
            print("Error: Could not import html_parser for validation.")
            return False
        
        for attempt in range(max_attempts):
            test_y = start_y + (attempt * step_size)
            test_pos = {"x": start_x, "y": test_y}
            
            print(f"Attempt {attempt + 1}/{max_attempts}: Testing capture point at ({start_x}, {test_y})")
            
            # Temporarily update the html_capture_point for testing
            original_capture_point = self.positions.get("html_capture_point")
            self.positions["html_capture_point"] = test_pos
            
            # Try to get HTML from this position
            html_content = self.get_html_from_screen()
            
            if html_content:
                # Test if HTML contains player areas
                try:
                    parsed_result = parser.parse_html(html_content)
                    players_data = parsed_result.get('all_players_data', [])
                    
                    # Check if we found player areas and they're not all empty
                    valid_players = [p for p in players_data if not p.get('is_empty', True)]
                    
                    if valid_players:
                        print(f"SUCCESS: Found valid capture point at ({start_x}, {test_y}) with {len(valid_players)} active players!")
                        
                        # Save the new capture point to config
                        self.save_config()
                        print("New HTML capture point saved to configuration.")
                        return True
                    else:
                        print(f"  HTML captured but no active players found.")
                        
                except Exception as e:
                    print(f"  Error parsing HTML: {e}")
            else:
                print(f"  No valid HTML captured.")
            
            # Restore original capture point for next attempt if this one failed
            if original_capture_point:
                self.positions["html_capture_point"] = original_capture_point
            else:
                self.positions.pop("html_capture_point", None)
        
        print(f"Failed to find valid HTML capture point after {max_attempts} attempts.")
        
        # Restore original capture point
        if original_capture_point:
            self.positions["html_capture_point"] = original_capture_point
        
        return False

    def get_html_from_screen_with_auto_retry(self, auto_retry=True):
        """
        Enhanced version of get_html_from_screen that automatically attempts to find a new capture point
        when "No 'div.player-area' elements found" occurs.
        
        Args:
            auto_retry (bool): Whether to attempt automatic recalibration on failure
            
        Returns:
            str: HTML content if successful, None if failed
        """
        if "html_capture_point" not in self.positions:
            print("Error: HTML capture point not calibrated.")
            return None
        
        # Check if auto-retry is enabled in config
        auto_search_enabled = self.config.get('auto_search', {}).get('enabled', True)
        if not auto_search_enabled:
            auto_retry = False
        
        # First, try the normal capture
        html_content = self.get_html_from_screen()
        
        if not html_content:
            if auto_retry:
                print("Initial HTML capture failed. Attempting automatic search for new capture point...")
                if self.auto_search_for_valid_html_capture_point():
                    # Try again with the new capture point
                    html_content = self.get_html_from_screen()
                    if html_content:
                        print("Successfully captured HTML with new capture point!")
                        return html_content
            return None
        
        # Test if the captured HTML contains player areas
        if auto_retry:
            try:
                from html_parser import PokerPageParser
                parser = PokerPageParser(logger=self.logger, config=self.config) # Pass logger and config
                parsed_result = parser.parse_html(html_content)
                players_data = parsed_result.get('all_players_data', [])
                
                # Check if we have valid player data
                valid_players = [p for p in players_data if not p.get('is_empty', True)]
                
                if not valid_players:
                    print("Warning: HTML captured but no active players found. Attempting automatic recalibration...")
                    if self.auto_search_for_valid_html_capture_point():
                        # Try again with the new capture point
                        new_html_content = self.get_html_from_screen()
                        if new_html_content:
                            print("Successfully captured HTML with new capture point after recalibration!")
                            return new_html_content
                    print("Automatic recalibration failed. Using original HTML content.")
                    
            except Exception as e:
                print(f"Error during HTML validation: {e}")
        
        return html_content

    def get_html_from_screen(self):
        if "html_capture_point" not in self.positions:
            print("Error: HTML capture point not calibrated.")
            return None
        
        capture_pos = self.positions["html_capture_point"]
        pyautogui.moveTo(capture_pos["x"], capture_pos["y"], duration=self.get_delay("short_pause"))
        pyautogui.click() # Click to focus the target area/window
        time.sleep(self.get_delay("short_pause")) # Increased pause for focus to settle
        
        # pyautogui.hotkey('ctrl', 'a') # Select all
        # time.sleep(0.2) # Increased pause after select all
        
        pyperclip.copy("") # Clear clipboard before attempting to copy
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(self.get_delay("medium_pause")) # Significantly increased pause for clipboard to update
        
        html_content = None
        for _ in range(3): # Try up to 3 times
            try:
                html_content = pyperclip.paste()
                if html_content and html_content.strip() and '<' in html_content and '>' in html_content:
                    break # Success
            except pyperclip.PyperclipWindowsException as e:
                print(f"Warning: pyperclip.paste() failed: {e}. Retrying...")
                time.sleep(0.5) # Wait a bit before retrying
            else: # If no exception but content is bad
                if not html_content or not html_content.strip() or '<' not in html_content or '>' not in html_content:
                    print(f"Warning: Clipboard does not seem to contain valid HTML-like content. Retrying...")
                    time.sleep(0.5) # Wait a bit before retrying
                else: # Content is good
                    break 
        
        # More lenient check for HTML-like content
        if not html_content or not html_content.strip() or '<' not in html_content or '>' not in html_content:
            print("Warning: Clipboard does not seem to contain valid HTML-like content.")
            print(f"Clipboard content (first 200 chars): '{html_content[:200]}'") 
            return None
        return html_content

    def _click_position(self, name, duration=0.2, randomize=False):
        if name not in self.positions:
            print(f"Error: Position '{name}' not calibrated.")
            return False
        
        pos = self.positions[name]
        x, y = pos['x'], pos['y']

        if randomize:
            offset_x = random.randint(-3, 3) # Random offset between -3 and 3 pixels for x
            offset_y = random.randint(-3, 3) # Random offset between -3 and 3 pixels for y
            x += offset_x
            y += offset_y
            # print(f"Randomized click for '{name}' to ({x}, {y}) from ({pos['x']}, {pos['y']})") # Optional for debugging

        pyautogui.moveTo(x, y, duration=duration)
        pyautogui.click()
        print(f"Clicked on '{name}' at ({x}, {y})")
        return True

    def action_fold(self):
        return self._click_position("fold_button", randomize=True)

    def action_check_call(self):
        return self._click_position("check_call_button", randomize=True)

    def action_all_in(self):
        """Perform an all-in action by clicking the all-in button."""
        return self._click_position("all_in_button", randomize=True)

    def action_raise(self, amount):
        if not amount:
            print("Error: Raise amount not provided for action_raise.")
            return False

        # 1. Click the initial raise button (to open/focus the input area)
        if not self._click_position("raise_button", randomize=True):
            print("Failed to click initial raise button.")
            return False
        time.sleep(self.get_delay("short_pause")) # Brief pause for UI to update (e.g., input field to appear/be ready)

        # 2. Click the raise input field
        if "raise_input_field" not in self.positions:
            print("Error: Position 'raise_input_field' not calibrated.")
            return False
        
        # Clicking the input field itself, also randomized
        if not self._click_position("raise_input_field", randomize=True):
            print("Failed to click raise input field.")
            return False
        time.sleep(0.2) # Pause for field to activate

        # 3. Clear the input field (optional, but good practice) and type the amount
        # Select all (Ctrl+A) and delete, handles existing values
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(self.get_delay("short_pause"))
        pyautogui.press('delete') # or 'backspace'
        time.sleep(self.get_delay("short_pause"))
        pyautogui.typewrite(str(amount), interval=0.05)
        print(f"Typed raise amount: {amount}")
        time.sleep(self.get_delay("short_pause"))

        # 4. Click the confirm raise button
        if not self._click_position("confirm_raise_button", randomize=True):
            print("Failed to click confirm raise button.")
            return False
        
        print(f"Raise action for amount '{amount}' completed.")
        return True

    def get_delay(self, delay_name):
        """Retrieve a delay value by name from the loaded configuration or defaults."""
        return self.delays.get(delay_name, 1.0) # Default to 1.0 second if not found

if __name__ == '__main__':
    ui = UIController()
    # ui.calibrate_all() # Uncomment to run calibration
    
    if not ui.positions:
        print("No positions calibrated. Run calibrate_all() first.")
    else:
        print("Current calibrated positions:", ui.positions)
        # Example usage (after calibration):
        # print("Attempting to get HTML...")
        # html = ui.get_html_from_screen()
        # if html:
        #     print("Successfully retrieved HTML (first 100 chars):", html[:100])
        # else:
        #     print("Failed to retrieve HTML.")
        
        # print("Simulating a fold action...")
        # ui.action_fold()
        # time.sleep(1)
        # print("Simulating a check/call action...")
        # ui.action_check_call()
        # time.sleep(1)
        # print("Simulating a raise action...")
        # ui.action_raise(amount="5BB") # Amount is conceptual here
