'''
Handles mouse control, screen capture, and other UI interactions.
'''
import pyautogui
import pyperclip
import time
import json
import random # Added for click randomization

CONFIG_FILE = "config.json"

class UIController:
    def __init__(self):
        self.positions = {}
        self.load_positions()

    def load_positions(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.positions = json.load(f)
        except FileNotFoundError:
            print(f"Info: {CONFIG_FILE} not found. Calibration needed.")
            self.positions = {}

    def save_positions(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.positions, f, indent=4)
        print(f"Positions saved to {CONFIG_FILE}")

    def calibrate_position(self, name):
        input(f"Move mouse to '{name}' and press Enter...")
        x, y = pyautogui.position()
        self.positions[name] = {"x": x, "y": y}
        print(f"Position '{name}' calibrated at ({x}, {y})")
        self.save_positions()

    def calibrate_all(self):
        print("Starting UI calibration process...")
        self.calibrate_position("html_capture_point") # Point to click for copying HTML
        self.calibrate_position("fold_button")
        self.calibrate_position("check_call_button") # Assumes check and call are the same button
        self.calibrate_position("all_in_button") # Added for the all-in scenario
        self.calibrate_position("raise_button") # This might be the button that opens the raise input
        self.calibrate_position("raise_input_field") # The actual input field for the amount
        self.calibrate_position("confirm_raise_button") # The button to confirm the raise after typing amount
        print("Calibration complete.")

    def get_html_from_screen(self):
        if "html_capture_point" not in self.positions:
            print("Error: HTML capture point not calibrated.")
            return None
        
        capture_pos = self.positions["html_capture_point"]
        pyautogui.moveTo(capture_pos["x"], capture_pos["y"], duration=0.2)
        pyautogui.click() # Click to focus the target area/window
        time.sleep(0.3) # Increased pause for focus to settle
        
        # pyautogui.hotkey('ctrl', 'a') # Select all
        # time.sleep(0.2) # Increased pause after select all
        
        pyperclip.copy("") # Clear clipboard before attempting to copy
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.5) # Significantly increased pause for clipboard to update
        
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

    def action_all_in(self): # New method for clicking all-in
        # This could be the same as check_call if the button text changes to "Call All-in"
        # Or it could be a separate button that appears.
        # If it's a distinct button, use "all_in_button". 
        # If the "check_call_button" becomes an "All-in Call" button, then that can be used.
        # For now, assuming a dedicated "all_in_button" might appear or the existing call button handles it.
        # The parser should ideally tell us which button to press (e.g. by identifying the specific all-in call button)
        # Let's assume for now there's a specific all_in_button if the action is a direct all-in bet/call.
        # If the decision is to CALL an all-in, action_check_call might be sufficient if that button handles it.
        # This method is more for when the bot decides to GO all-in itself, or if there's a specific button for calling an all-in.
        if self._click_position("all_in_button", randomize=True): # Try dedicated all_in_button first
            return True
        # Fallback to check_call_button if a dedicated all_in_button isn't found or fails,
        # as the call button might dynamically change to reflect an all-in call.
        print("All-in button not found or click failed, attempting check/call button for all-in call.")
        return self.action_check_call()

    def action_raise(self, amount=None):
        if not amount:
            print("Error: Raise amount not provided for action_raise.")
            return False

        # 1. Click the initial raise button (to open/focus the input area)
        if not self._click_position("raise_button", randomize=True):
            print("Failed to click initial raise button.")
            return False
        time.sleep(0.3) # Brief pause for UI to update (e.g., input field to appear/be ready)

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
        time.sleep(0.1)
        pyautogui.press('delete') # or 'backspace'
        time.sleep(0.1)
        pyautogui.typewrite(str(amount), interval=0.05)
        print(f"Typed raise amount: {amount}")
        time.sleep(0.2)

        # 4. Click the confirm raise button
        if not self._click_position("confirm_raise_button", randomize=True):
            print("Failed to click confirm raise button.")
            return False
        
        print(f"Raise action for amount '{amount}' completed.")
        return True

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
