import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from poker_bot import PokerBot
from html_parser import PokerPageParser # Changed from HTMLParser
from decision_engine import DecisionEngine # Assuming DecisionEngine might be needed for type hints or direct use

def run_test_with_html(html_file_path):
    """
    Runs a poker bot decision test using an HTML file as input.
    """
    print(f"Running test with HTML file: {html_file_path}")

    # Initialize HTMLParser
    parser = PokerPageParser() # Changed from HTMLParser()

    # Initialize PokerBot (assuming default config or a way to load it)
    # If your PokerBot or DecisionEngine requires specific config, load or define it here.
    # For example, using a default or a simple config for testing:
    config_data = {
        'big_blind': 0.02,  # Example value, adjust if necessary
        'small_blind': 0.01, # Example value, adjust if necessary
        # Add other necessary config parameters
        'strategy_profile': 'aggressive', # Example
        'bluff_frequency': 0.2, # Example
        'value_bet_threshold': 0.7, # Example
        'log_level': 'INFO',
        'log_file': 'poker_bot_test.log'
    }
    bot = PokerBot(config=config_data)

    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # game_state = parser.parse_html(file_path=html_file_path)
        game_state = parser.parse_html(html_content=html_content) # Corrected argument

        if not game_state or game_state.get('error'):
            print(f"Error parsing HTML: {game_state.get('error', 'Unknown error')}") # Replaced logger.error with print
            return

        # Identify my player and their seat
        my_player_seat = None
        # for i, player in enumerate(game_state['players']):
        for i, player in enumerate(game_state['all_players_data']): # Corrected key
            if player.get('is_my_player'):
                my_player_seat = player.get('seat')
                print(f"My player identified: {player.get('name')} at seat {my_player_seat}") # Replaced logger.info with print
                break

        if my_player_seat is None:
            print("Could not identify the bot's player in the game state.")
            print("Parsed players:", game_state['all_players_data'])
            return

        print(f"Bot identified as player seat: {my_player_seat}")
        # print(f"Game state for decision: {game_state}") # Replaced logger.info with print

        # action, amount = bot.make_decision(game_state) # Assuming make_decision is a method of PokerBot
        action, amount = bot.run_test_file(html_file_path)

        print(f"Bot action: {action}, Amount: {amount}") # Replaced logger.info with print

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Construct the absolute path to the HTML file
    # Assuming the script is run from the root of the pokerplayer directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(script_dir, "examples", "flop_my_turn_raised.html")
    
    if not os.path.exists(html_file):
        print(f"HTML file not found: {html_file}")
    else:
        run_test_with_html(html_file)
