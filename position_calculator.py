"""
Enhanced position calculator for poker games.
This module provides reliable position calculation for poker tables,
properly handling empty seats and different table sizes.
"""

import logging

# Setup dedicated logger for position calculation
position_logger = logging.getLogger('position_calculator')
position_logger.setLevel(logging.INFO)

# Create handlers if they don't exist yet
if not position_logger.handlers:
    # Create a file handler
    file_handler = logging.FileHandler('position_calculation.log')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    position_logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    position_logger.addHandler(console_handler)

def calculate_positions(player_data, dealer_position):
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
    
    try:
        dealer_seat = int(dealer_position)
        position_logger.info(f"Dealer seat converted to integer: {dealer_seat}")
    except (ValueError, TypeError):
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
    active_players = []
    try:
        active_players = sorted(
            [p for p in player_data if not p.get('is_empty', False) and p.get('seat') is not None],
            key=lambda x: int(x['seat'])
        )
    except (ValueError, TypeError) as e:
        position_logger.error(f"Error sorting active players: {e}. Check if all seat numbers are valid integers.")
        return player_data
    
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
                if num_players == 5:
                    # With 5 players, we have BTN, SB, BB, UTG, CO
                    co_idx = (dealer_idx + 4) % num_players
                    active_players[co_idx]['position'] = 'CO'
                    position_logger.info(f"  CO: Seat {active_players[co_idx]['seat']}, "
                                        f"Name: {active_players[co_idx].get('name', 'N/A')}")
                elif num_players == 6:
                    # With 6 players, we have BTN, SB, BB, UTG, MP, CO
                    mp_idx = (dealer_idx + 4) % num_players
                    co_idx = (dealer_idx + 5) % num_players
                    
                    active_players[mp_idx]['position'] = 'MP'
                    active_players[co_idx]['position'] = 'CO'
                    
                    position_logger.info(f"  MP: Seat {active_players[mp_idx]['seat']}, "
                                        f"Name: {active_players[mp_idx].get('name', 'N/A')}")
                    position_logger.info(f"  CO: Seat {active_players[co_idx]['seat']}, "
                                        f"Name: {active_players[co_idx].get('name', 'N/A')}")
                else:
                    # Handle 7+ players: BTN, SB, BB, UTG, UTG+1/MP1, MP2, ..., CO
                    position_logger.info(f"Table with {num_players} players detected")
                    
                    # First assign the cutoff position (right before the dealer)
                    co_idx = (dealer_idx - 1) % num_players
                    if co_idx < 0:
                        co_idx += num_players
                    active_players[co_idx]['position'] = 'CO'
                    position_logger.info(f"  CO: Seat {active_players[co_idx]['seat']}, "
                                       f"Name: {active_players[co_idx].get('name', 'N/A')}")
                    
                    # Now assign the positions between UTG and CO
                    # Start with UTG+1 and continue to positions right before CO
                    current_idx = (utg_idx + 1) % num_players
                    position_count = 1
                    
                    while current_idx != co_idx:
                        # For 7-8 players: MP1, MP2, etc.
                        # For 9+ players: UTG+1, UTG+2, MP1, MP2, etc.
                        if position_count == 1 and num_players >= 9:
                            position_name = "UTG+1"
                        elif position_count == 2 and num_players >= 9:
                            position_name = "UTG+2"
                        else:
                            # Standard MP naming for middle positions
                            position_name = f"MP{position_count}"
                        
                        active_players[current_idx]['position'] = position_name
                        position_logger.info(f"  {position_name}: Seat {active_players[current_idx]['seat']}, "
                                           f"Name: {active_players[current_idx].get('name', 'N/A')}")
                        
                        position_count += 1
                        current_idx = (current_idx + 1) % num_players
    
    # Create a mapping from seat numbers to positions
    seat_to_position = {}
    for player in active_players:
        if 'position' in player and player.get('seat') is not None:
            seat_to_position[player['seat']] = player['position']
    
    # Update the positions in the original player data
    for player in player_data:
        if not player.get('is_empty', False) and player.get('seat') in seat_to_position:
            player['position'] = seat_to_position[player['seat']]
            if player.get('is_my_player', False):
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
    # Example usage/testing
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
        updated_data = calculate_positions(test_player_data, str(dealer_pos))
