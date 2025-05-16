'''
Configuration for the Poker Bot, including UI positions if not using a dedicated config file.
This file is largely superseded by ui_controller.py's use of config.json for positions.
Keeping it minimal or for other bot-wide settings.
'''

# Example: Poker table window title (if needed for focusing the window)
POKER_TABLE_WINDOW_TITLE = "PokerStars" # Replace with actual window title if used

# Other bot settings can go here
LOG_LEVEL = "INFO"

# UI positions will be stored in config.json by ui_controller.py
# Example structure (managed by UIController):
# POSITIONS = {
#     "html_capture_point": {"x": 100, "y": 200},
#     "fold_button": {"x": 300, "y": 400},
#     "check_call_button": {"x": 500, "y": 600},
#     "raise_button": {"x": 700, "y": 800}
# }
