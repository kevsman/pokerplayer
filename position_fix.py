"""
Enhanced version of position calculation that properly handles empty seats
and provides detailed logging to help diagnose position assignment issues.
"""

import logging

# Setup dedicated logger for position calculation
position_logger = logging.getLogger('position_calculator')
position_logger.setLevel(logging.DEBUG)

# Create a file handler
file_handler = logging.FileHandler('position_fix.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
position_logger.addHandler(file_handler)

def calculate_player_positions(player_data, dealer_position):
    """
    Calculate poker player positions based on dealer position.
    
    Args:
        player_data: List of player dictionaries
        dealer_position: The seat number of the dealer
    
    Returns:
        The updated player_data with positions assigned
    """
    position_logger.info(f"Starting position calculation with dealer position: {dealer_position}")
    
    if not player_data:
        position_logger.warning("No player data provided. Returning empty list.")
        return []
    
    if not dealer_position or dealer_position == "N/A":
        position_logger.warning("Invalid dealer position. Cannot calculate player positions.")
        return player_data
    
    try:
        dealer_seat = int(dealer_position)
        position_logger.info(f"Dealer seat converted to integer: {dealer_seat}")
    except ValueError:
        position_logger.error(f"Could not convert dealer_position '{dealer_position}' to an integer.")
        return player_data
    
    # Log raw player data
    position_logger.debug("Raw player data received:")
    for i, player in enumerate(player_data):
        position_logger.debug(f"  Player {i}: Seat {player.get('seat', 'N/A')}, "
                              f"Name {player.get('name', 'N/A')}, "
                              f"Is empty: {player.get('is_empty', False)}, "
                              f"Is my player: {player.get('is_my_player', False)}")
    
    # Filter to active (non-empty) players and sort by seat number
    active_players = sorted(
        [p for p in player_data if not p.get('is_empty', False) and p.get('seat') is not None],
        key=lambda x: int(x['seat'])
    )
    
    position_logger.info(f"Filtered and sorted {len(active_players)} active players:")
    for i, player in enumerate(active_players):
        position_logger.info(f"  Index {i}: Seat {player.get('seat')}, Name: {player.get('name', 'N/A')}")
    
    num_players = len(active_players)
    if num_players == 0:
        position_logger.warning("No active players found after filtering.")
        return player_data
    
    # Find dealer's index in the sorted active players list
    dealer_idx = -1
    for i, player in enumerate(active_players):
        if int(player['seat']) == dealer_seat:
            dealer_idx = i
            break
    
    if dealer_idx == -1:
        position_logger.warning(f"Dealer seat {dealer_seat} not found in active players. "
                               f"This may happen if the dealer position is at an empty seat.")
        # In this case, we'll return the original player_data without positions
        return player_data
    
    position_logger.info(f"Found dealer at index {dealer_idx} in sorted active players list")
    
    # Clear out any existing position data to avoid confusion
    for player in active_players:
        if 'position' in player:
            del player['position']
    
    # Assign positions based on number of players
    if num_players == 2:  # Heads-up
        position_logger.info("Assigning positions for 2-player game (heads-up)")
        # In heads-up, dealer is SB and other player is BB
        sb_idx = dealer_idx
        bb_idx = (dealer_idx + 1) % num_players
        
        active_players[sb_idx]['position'] = 'SB'
        active_players[bb_idx]['position'] = 'BB'
        
        position_logger.info(f"  SB (Dealer): Seat {active_players[sb_idx]['seat']}, "
                            f"Name: {active_players[sb_idx].get('name', 'N/A')}")
        position_logger.info(f"  BB: Seat {active_players[bb_idx]['seat']}, "
                            f"Name: {active_players[bb_idx].get('name', 'N/A')}")
    else:  # 3+ players
        position_logger.info(f"Assigning positions for {num_players}-player game (standard positions)")
        
        # Assign BTN, SB, BB
        btn_idx = dealer_idx
        sb_idx = (dealer_idx + 1) % num_players
        bb_idx = (dealer_idx + 2) % num_players
        
        active_players[btn_idx]['position'] = 'BTN'
        active_players[sb_idx]['position'] = 'SB'
        active_players[bb_idx]['position'] = 'BB'
        
        position_logger.info(f"  BTN (Dealer): Seat {active_players[btn_idx]['seat']}, "
                            f"Name: {active_players[btn_idx].get('name', 'N/A')}")
        position_logger.info(f"  SB: Seat {active_players[sb_idx]['seat']}, "
                            f"Name: {active_players[sb_idx].get('name', 'N/A')}")
        position_logger.info(f"  BB: Seat {active_players[bb_idx]['seat']}, "
                            f"Name: {active_players[bb_idx].get('name', 'N/A')}")
        
        # Assign remaining positions based on table size
        if num_players >= 4:
            utg_idx = (dealer_idx + 3) % num_players
            active_players[utg_idx]['position'] = 'UTG'
            position_logger.info(f"  UTG: Seat {active_players[utg_idx]['seat']}, "
                                f"Name: {active_players[utg_idx].get('name', 'N/A')}")
        
        if num_players >= 5:
            co_idx = (dealer_idx + 4) % num_players
            active_players[co_idx]['position'] = 'CO'
            position_logger.info(f"  CO: Seat {active_players[co_idx]['seat']}, "
                                f"Name: {active_players[co_idx].get('name', 'N/A')}")
        
        if num_players == 6:
            mp_idx = (dealer_idx + 4) % num_players
            co_idx = (dealer_idx + 5) % num_players
            
            # Update assignments for 6 players
            active_players[mp_idx]['position'] = 'MP'
            active_players[co_idx]['position'] = 'CO'
            
            position_logger.info(f"  MP: Seat {active_players[mp_idx]['seat']}, "
                                f"Name: {active_players[mp_idx].get('name', 'N/A')}")
            position_logger.info(f"  CO: Seat {active_players[co_idx]['seat']}, "
                                f"Name: {active_players[co_idx].get('name', 'N/A')} (updated for 6 players)")
        
        if num_players > 6:
            position_logger.info(f"Table with {num_players} players detected")
            # Handle UTG+1, UTG+2, etc. for larger tables
            # For now we'll just use MP for all positions between UTG and CO
            for i in range(4, num_players):
                idx = (dealer_idx + i) % num_players
                if i == num_players - 1:
                    active_players[idx]['position'] = 'CO'
                    position_logger.info(f"  CO: Seat {active_players[idx]['seat']}, "
                                        f"Name: {active_players[idx].get('name', 'N/A')}")
                else:
                    mp_name = f"MP" if i == 4 else f"MP{i-3}"  # MP, MP2, MP3, etc.
                    active_players[idx]['position'] = mp_name
                    position_logger.info(f"  {mp_name}: Seat {active_players[idx]['seat']}, "
                                        f"Name: {active_players[idx].get('name', 'N/A')}")
    
    # Create a mapping from seat numbers to positions for easy lookup
    seat_to_position = {}
    for player in active_players:
        if 'position' in player:
            seat_to_position[player['seat']] = player['position']
    
    # Update the positions in the original player data
    for player in player_data:
        if not player.get('is_empty') and player.get('seat') in seat_to_position:
            player['position'] = seat_to_position[player['seat']]
            if player.get('is_my_player'):
                position_logger.info(f"MY PLAYER assigned position: {player['position']} in seat {player['seat']}, "
                                   f"Name: {player.get('name', 'N/A')}")
    
    # Log the final position assignments for all players
    position_logger.info("Final position assignments:")
    for player in player_data:
        position = player.get('position', 'None')
        position_logger.info(f"  Seat {player.get('seat', 'N/A')}: {position}, "
                           f"Name: {player.get('name', 'N/A')}, "
                           f"Is my player: {player.get('is_my_player', False)}")
    
    return player_data

if __name__ == "__main__":
    # Example usage
    test_player_data = [
        {'seat': '1', 'name': 'Player1', 'is_my_player': False, 'is_empty': False},
        {'seat': '2', 'name': 'Player2', 'is_my_player': False, 'is_empty': False},
        {'seat': '3', 'name': 'EmptySeat', 'is_empty': True},
        {'seat': '4', 'name': 'MyPlayer', 'is_my_player': True, 'is_empty': False},
        {'seat': '5', 'name': 'Player5', 'is_my_player': False, 'is_empty': False},
        {'seat': '6', 'name': 'Player6', 'is_my_player': False, 'is_empty': False},
    ]
    
    # Test with different dealer positions
    for dealer_pos in range(1, 7):
        position_logger.info(f"\n--- Testing with dealer in seat {dealer_pos} ---")
        updated_data = calculate_player_positions(test_player_data, str(dealer_pos))
