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
    "after_action_delay": 2.5, # seconds
    "short_pause": 0.25, # seconds
    "medium_pause": 0.5, # seconds
    "long_pause": 1.0 # seconds
}

class UIController:
    def __init__(self):
        self.positions = {}
        self.delays = DEFAULT_DELAYS.copy() # Initialize with defaults
        self.load_config()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                self.positions = config_data.get("positions", {})
                # Load delays, merging with defaults to ensure all keys are present
                loaded_delays = config_data.get("delays", {})
                for key, value in loaded_delays.items():
                    if key in self.delays: # Only update if key is a recognized delay setting
                        self.delays[key] = value
        except FileNotFoundError:
            print(f"Info: {CONFIG_FILE} not found. Using default positions and delays. Calibration needed.")
            self.positions = {}
            self.delays = DEFAULT_DELAYS.copy()
        except json.JSONDecodeError:
            print(f"Error: Could not decode {CONFIG_FILE}. Using default positions and delays.")
            self.positions = {}
            self.delays = DEFAULT_DELAYS.copy()

    def save_config(self):
        config_data = {
            "positions": self.positions,
            "delays": self.delays
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"Configuration (positions and delays) saved to {CONFIG_FILE}")

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
        self.calibrate_position("html_capture_point") # Point to click for copying HTML
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
        
        html_content = pyperclip.paste()
        
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
