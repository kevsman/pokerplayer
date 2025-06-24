import requests
import logging

class DeepStackClient:
    """
    Client for communicating with a running DeepStack Poker AI server.
    Assumes DeepStack is running and listening on localhost:8500 (default).
    """
    def __init__(self, host='localhost', port=8500, logger=None):
        self.base_url = f"http://{host}:{port}"
        self.logger = logger or logging.getLogger(__name__)

    def get_action(self, game_state):
        """
        Sends the game state to DeepStack and returns the recommended action.
        :param game_state: dict with keys like 'players', 'community', 'pot', etc.
        :return: dict with action info, e.g. {'action': 'raise', 'amount': 2.5}
        """
        url = f"{self.base_url}/api/v1/action"
        try:
            response = requests.post(url, json=game_state, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Expected DeepStack response: {'action': 'fold'|'call'|'raise', 'amount': float}
            return data
        except Exception as e:
            self.logger.error(f"DeepStack API error: {e}")
            return {'action': 'fold', 'amount': 0}

    def get_action_from_internal_state(self, internal_state, my_player_index=None):
        """
        Converts your internal game state to DeepStack format, calls DeepStack, and returns the action.
        :param internal_state: dict as used in your PokerBot (see poker_bot.py)
        :param my_player_index: index of the acting player (optional, if not in state)
        :return: dict with action info, e.g. {'action': 'raise', 'amount': 2.5}
        """
        # Extract and map fields from your internal state to DeepStack's expected format
        # DeepStack expects: players, community, pot, to_call, min_raise, max_raise, position, round
        players = []
        for p in internal_state.get('players', []):
            player = {
                'name': p.get('name', ''),
                'stack': float(p.get('stack', 0)),
                'bet': float(p.get('bet', 0)),
            }
            if p.get('is_my_player') or (my_player_index is not None and internal_state['players'].index(p) == my_player_index):
                player['is_my_player'] = True
                if 'hand' in p and p['hand']:
                    player['hand'] = p['hand']
                elif 'cards' in p and p['cards']:
                    player['hand'] = p['cards']
            players.append(player)

        # Community cards
        community = internal_state.get('community_cards') or internal_state.get('board') or []
        # Pot size
        pot = float(internal_state.get('pot_size', 0))
        # To call (amount needed to call)
        my_player = None
        if my_player_index is not None and 0 <= my_player_index < len(internal_state.get('players', [])):
            my_player = internal_state['players'][my_player_index]
        else:
            for p in internal_state.get('players', []):
                if p.get('is_my_player'):
                    my_player = p
                    break
        to_call = float(my_player.get('bet_to_call', 0) if my_player else 0)
        # Min/max raise
        min_raise = float(internal_state.get('min_raise', 0))
        max_raise = float(my_player.get('stack', 0) if my_player else 0)
        # Position (index at table)
        position = my_player_index if my_player_index is not None else 0
        # Round/street
        round_name = internal_state.get('current_round') or internal_state.get('street') or 'preflop'
        # Compose DeepStack game state
        ds_game_state = {
            'players': players,
            'community': community,
            'pot': pot,
            'to_call': to_call,
            'min_raise': min_raise,
            'max_raise': max_raise,
            'position': position,
            'round': round_name,
        }
        return self.get_action(ds_game_state)

# Example usage:
if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    client = DeepStackClient()
    # Example game state (must match DeepStack's expected format)
    game_state = {
        "players": [
            {"name": "Hero", "stack": 100, "bet": 2, "hand": ["Ah", "Kd"], "is_my_player": True},
            {"name": "Villain1", "stack": 100, "bet": 2},
            # ... up to 6 players
        ],
        "community": ["2c", "7d", "Jh"],
        "pot": 6,
        "to_call": 2,
        "min_raise": 4,
        "max_raise": 100,
        "position": 2,
        "round": "flop",
        # Add any other required fields for DeepStack
    }
    action = client.get_action(game_state)
    print("DeepStack action:", action)
