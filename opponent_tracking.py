# opponent_tracking.py
# Enhanced opponent modeling and tracking for poker bot

import logging
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any # Added Any
import time # For generating placeholder hand IDs

# logger = logging.getLogger(__name__) # Will be passed in

# Define constants for streets to ensure consistency
PREFLOP = "preflop"
FLOP = "flop"
TURN = "turn"
RIVER = "river"
STREETS = [PREFLOP, FLOP, TURN, RIVER]

class OpponentProfile:
    """
    Track and analyze opponent tendencies for better decision making.
    """
    
    def __init__(self, player_name: str, max_hands_tracked: int = 100, max_actions_per_hand: int = 20, logger_instance: Optional[logging.Logger] = None):
        self.player_name = player_name
        self.max_hands_tracked = max_hands_tracked
        self.max_actions_per_hand = max_actions_per_hand
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        
        # Basic stats
        self.hands_played_count = 0 # Renamed for clarity
        self.hands_seen_count = 0   # Renamed for clarity
        
        # Preflop stats
        self.preflop_opportunities = 0
        self.preflop_vpip_actions = 0 # VPIP: Voluntarily Put Money In Pot (Call or Raise)
        self.preflop_pfr_actions = 0  # PFR: Preflop Raise actions
        
        # Positional stats (VPIP, PFR, 3-bet, Fold to 3-bet, etc.)
        # Structure: self.position_stats[position][stat_name]
        self.position_stats = defaultdict(lambda: defaultdict(int))

        # Postflop stats per street
        # Structure: self.street_stats[street][stat_name]
        self.street_stats = defaultdict(lambda: defaultdict(int))
        # Examples:
        # C-bet opportunity / C-bet made (Flop, Turn, River)
        # Fold to C-bet (Flop, Turn, River)
        # Aggression Frequency (AFq) = (Bets + Raises) / (Bets + Raises + Calls + Folds) * 100
        # Went to Showdown (WTSD)
        # Won at Showdown (W$SD)
        # Won When Saw Flop (WWSF)

        # Recent hand history (tracking actions within specific hands)
        # Stores a list of actions for the last N hands. Each hand is a list of action dicts.
        self.hand_action_history: deque[Dict[str, List[Dict[str, Any]]]] = deque(maxlen=max_hands_tracked)
        self.current_hand_actions: List[Dict[str, Any]] = [] # Actions for the hand currently being processed
        self.current_hand_id: Optional[str] = None
        
        # Bet sizing patterns (can be enhanced)
        self.bet_sizes = {
            PREFLOP: defaultdict(list),
            FLOP: defaultdict(list),
            TURN: defaultdict(list),
            RIVER: defaultdict(list)
        }
        
    def new_hand(self, hand_id: str):
        """Called at the start of a new hand to reset current hand data."""
        if self.current_hand_id and self.current_hand_actions: 
            
            if len(self.current_hand_actions) > self.max_actions_per_hand:
                 self.logger.warning(f"Player {self.player_name}, Hand {self.current_hand_id}: Exceeded max_actions_per_hand ({len(self.current_hand_actions)} > {self.max_actions_per_hand}). Truncating.")
                 self.current_hand_actions = self.current_hand_actions[:self.max_actions_per_hand]

            self.hand_action_history.append({
                "hand_id": self.current_hand_id,
                "actions": list(self.current_hand_actions) # Store a copy
            })
        self.current_hand_actions = []
        self.current_hand_id = hand_id
        self.hands_seen_count += 1 # Increment when a new hand starts and player is involved        # Reset per-hand flags (e.g., for C-bet opportunities)
        self._reset_per_hand_street_flags()

    def _reset_per_hand_street_flags(self):
        """Resets flags that are specific to a hand and street, e.g., cbet opportunity."""
        self.saw_flop_this_hand = False
        self.was_preflop_aggressor_this_hand = False
        self.cbet_opportunity_flop = False
        self.cbet_opportunity_turn = False
        self.cbet_opportunity_river = False
        self.faced_cbet_flop = False
        self.faced_cbet_turn = False
        self.faced_cbet_river = False
        
        # Reset per-hand counting flags
        self._preflop_opportunity_counted_this_hand = False
        self._vpip_counted_this_hand = False
        self._pfr_counted_this_hand = False


    def log_action(self, action_type: str, street: str, amount: float = 0, pot_size_before_action: float = 0, 
                     position: Optional[str] = None, is_our_hero: bool = False, players_in_hand_at_action: int = 0):
        """
        Logs a single action taken by the opponent.
        This is the primary method for updating opponent statistics.
        """
        if not self.current_hand_id:
            self.logger.warning(f"Player {self.player_name}: Log_action called without current_hand_id. Action: {action_type} on {street}")
            # Initialize a placeholder hand_id for tracking
            self.current_hand_id = f"unknown_{int(time.time())}"
            self.logger.info(f"Created placeholder hand_id: {self.current_hand_id} for {self.player_name}")

        action_record = {
            "action_type": action_type.upper(), # Standardize to uppercase
            "street": street.lower(),
            "amount": amount,
            "pot_size_before_action": pot_size_before_action,
            "position": position,
            "players_in_hand_at_action": players_in_hand_at_action,
            # Add more context if needed, e.g., board cards at time of action
        }
        self.current_hand_actions.append(action_record)
        
        # Enhanced logging for debugging
        self.logger.debug(f"Player {self.player_name}: Logged action {action_type} on {street} - Total actions this hand: {len(self.current_hand_actions)}")

        # --- PREFLOP Stats ---
        if street.lower() == PREFLOP:
            # This assumes player is dealt cards if an action is logged for them preflop
            # A more robust way would be to have an explicit "dealt_in" signal per hand
            if not hasattr(self, '_preflop_opportunity_counted_this_hand') or not self._preflop_opportunity_counted_this_hand:
                self.preflop_opportunities += 1
                self._preflop_opportunity_counted_this_hand = True # Flag to count only once per hand
                self.logger.debug(f"Player {self.player_name}: Preflop opportunity counted. Total: {self.preflop_opportunities}")

            action_upper = action_type.upper()
            if action_upper in ["CALL", "BET", "RAISE"]:
                if not hasattr(self, '_vpip_counted_this_hand') or not self._vpip_counted_this_hand:
                    self.preflop_vpip_actions += 1
                    self._vpip_counted_this_hand = True # Count VPIP only once per hand
                    self.logger.debug(f"Player {self.player_name}: VPIP action counted. Total: {self.preflop_vpip_actions}")
                if position:
                    self.position_stats[position]["vpip_hands"] += 1

            if action_upper in ["BET", "RAISE"]: # PFR includes open bets (limped pot) or raises
                if not hasattr(self, '_pfr_counted_this_hand') or not self._pfr_counted_this_hand:
                    self.preflop_pfr_actions += 1
                    self._pfr_counted_this_hand = True # Count PFR only once per hand
                    self.was_preflop_aggressor_this_hand = True
                    self.logger.debug(f"Player {self.player_name}: PFR action counted. Total: {self.preflop_pfr_actions}")
                if position:
                    self.position_stats[position]["pfr_hands"] += 1
                
                # Store bet sizing (as ratio to pot or BBs)
                if pot_size_before_action > 0 and amount > 0: # Basic bet sizing as % of pot
                     self.bet_sizes[PREFLOP][action_upper].append(amount / pot_size_before_action)

        # --- POSTFLOP Stats ---
        elif street.lower() in [FLOP, TURN, RIVER]:
            street_lower = street.lower()
            
            # Track total actions on street for aggression frequency calculation
            self.street_stats[street_lower]["total_actions_on_street"] += 1
            
            action_upper = action_type.upper()
            self.street_stats[street_lower][f"{action_upper}_count"] += 1
            
            # Bet sizing tracking for postflop
            if action_upper in ["BET", "RAISE"] and pot_size_before_action > 0 and amount > 0:
                self.bet_sizes[street_lower][action_upper].append(amount / pot_size_before_action)
            
            self.logger.debug(f"Player {self.player_name}: Postflop action {action_type} on {street_lower} - Street total actions: {self.street_stats[street_lower]['total_actions_on_street']}")

        # --- General Action Tracking ---
        # Increment hands played if this is their first action of the hand
        if len(self.current_hand_actions) == 1:
            self.hands_played_count += 1
            self.logger.debug(f"Player {self.player_name}: First action of hand. Hands played: {self.hands_played_count}")

        # Reset per-hand flags at the start of a new hand via new_hand()
        if street == PREFLOP and action_type.upper() == "FOLD": # If player folds preflop
            self._preflop_opportunity_counted_this_hand = False # Reset for next hand
            self._vpip_counted_this_hand = False
            self._pfr_counted_this_hand = False


    def get_vpip(self) -> float:
        if self.preflop_opportunities == 0: return 0.0
        return (self.preflop_vpip_actions / self.preflop_opportunities) * 100

    def get_pfr(self) -> float:
        if self.preflop_opportunities == 0: return 0.0
        return (self.preflop_pfr_actions / self.preflop_opportunities) * 100
    
    def get_cbet_stat(self, street: str) -> Tuple[float, int]:
        """Returns C-bet percentage and number of opportunities for the street."""
        if street not in [FLOP, TURN, RIVER]: return 0.0, 0
        
        opportunities = self.street_stats[street].get("cbet_opportunities", 0)
        cbets_made = self.street_stats[street].get("cbets_made", 0)
        
        if opportunities == 0: return 0.0, 0
        return (cbets_made / opportunities) * 100, opportunities

    def get_fold_to_cbet_stat(self, street: str) -> Tuple[float, int]:
        """Returns Fold to C-bet percentage and number of opportunities."""
        # This requires tracking when player FACED a cbet
        # For now, placeholder:
        opportunities = self.street_stats[street].get("faced_cbet_opportunities", 0)
        folds_to_cbet = self.street_stats[street].get("fold_to_cbet_count", 0)
        if opportunities == 0: return 0.0, 0
        return (folds_to_cbet / opportunities) * 100, opportunities

    def get_aggression_frequency(self, street: Optional[str] = None) -> float:
        """Calculates Aggression Frequency (AFq). (Bets + Raises) / (Total Actions) * 100"""
        bets = 0
        raises = 0
        total_actions = 0

        streets_to_consider = [street] if street else [FLOP, TURN, RIVER]

        for s in streets_to_consider:
            bets += self.street_stats[s].get("BET_count", 0) + self.street_stats[s].get("OPEN_BET_count",0) # Assuming OPEN_BET for limped pots
            raises += self.street_stats[s].get("RAISE_count", 0)
            total_actions += self.street_stats[s].get("total_actions_on_street",0)
            # More robust: total_actions = bets + raises + calls + folds + checks on that street

        if total_actions == 0: return 0.0
        return ((bets + raises) / total_actions) * 100
        
    def get_average_bet_size(self, street: str, action_type: str) -> Optional[float]:
        """Get average bet size ratio for specific street and action type (e.g. FLOP, BET)."""
        sizes = self.bet_sizes.get(street, {}).get(action_type.upper(), [])
        if not sizes:
            return None
        return sum(sizes) / len(sizes)

    def classify_player_type(self) -> str:
        vpip = self.get_vpip()
        pfr = self.get_pfr()
        afq_flop = self.get_aggression_frequency(FLOP) # Example: use flop AFq

        if self.hands_seen_count < 20: # Need a minimum sample size
            return "unknown_low_sample"

        if vpip < 20: # Tight
            if pfr < (vpip * 0.5): # Significantly lower PFR than VPIP -> Passive
                return "tight_passive" # (e.g. 18/7)
            elif pfr > (vpip * 0.75): # PFR close to VPIP -> Aggressive
                 return "tight_aggressive" # (e.g. 18/15 TAG)
            else: # In between
                return "tight_moderate" 
        elif vpip <= 35: # Loose
            if pfr < (vpip * 0.4):
                return "loose_passive" # (e.g. 30/10 Fish)
            elif pfr > (vpip * 0.65):
                return "loose_aggressive" # (e.g. 30/25 LAG)
            else:
                return "loose_moderate"
        else: # Very Loose (Whale/Maniac)
            if pfr < (vpip * 0.5):
                return "whale" # (e.g. 50/15 Calling Station / Whale)
            else:
                return "maniac" # (e.g. 50/40 Maniac)
                
    def __str__(self) -> str:
        return (f"OpponentProfile({self.player_name}): "
                f"VPIP={self.get_vpip():.1f} ({self.preflop_vpip_actions}/{self.preflop_opportunities}), "
                f"PFR={self.get_pfr():.1f} ({self.preflop_pfr_actions}/{self.preflop_opportunities}), "
                f"HandsSeen={self.hands_seen_count}, Type={self.classify_player_type()}")


class OpponentTracker:
    """
    Manages multiple OpponentProfile instances and provides aggregated table insights.
    """
    def __init__(self, config=None, logger_instance: Optional[logging.Logger] = None, max_hands_to_track_per_opponent: int = 100):
        self.opponents: Dict[str, OpponentProfile] = {}
        self.config = config # Store config if provided
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        self.max_hands_to_track_per_opponent = max_hands_to_track_per_opponent
        self.logger.info("OpponentTracker initialized.")

    def get_opponent_profile(self, player_name: str) -> OpponentProfile:
        """Retrieves or creates an opponent profile."""
        if player_name not in self.opponents:
            self.logger.info(f"Creating new profile for opponent: {player_name}")
            self.opponents[player_name] = OpponentProfile(
                player_name,
                max_hands_tracked=self.max_hands_to_track_per_opponent,
                logger_instance=self.logger # Pass logger to profile
            )
        return self.opponents[player_name]

    def log_action(self, player_name: str, action_type: str, street: str, amount: float = 0, 
                   pot_size_before_action: float = 0, position: Optional[str] = None, 
                   is_our_hero: bool = False, players_in_hand_at_action: int = 0, hand_id: Optional[str] = None):
        """
        Logs an action for a specific opponent.
        Ensures the hand_id is passed to the profile's new_hand if it's a new hand for them.
        """
        if not player_name: # Basic validation
            self.logger.warning("Attempted to log action for player with no name.")
            return

        profile = self.get_opponent_profile(player_name)
        
        # Check if it's a new hand for this player profile
        if hand_id and profile.current_hand_id != hand_id:
            profile.new_hand(hand_id)
            self.logger.debug(f"New hand ({hand_id}) started for opponent {player_name} in OpponentTracker.")
        elif not profile.current_hand_id and hand_id: # If profile just created and hand_id is available
            profile.new_hand(hand_id)
            self.logger.debug(f"Initial hand ({hand_id}) set for new opponent {player_name} in OpponentTracker.")

        profile.log_action(
            action_type=action_type, 
            street=street, 
            amount=amount, 
            pot_size_before_action=pot_size_before_action,
            position=position,
            is_our_hero=is_our_hero,
            players_in_hand_at_action=players_in_hand_at_action
        )
            
    def get_table_dynamics(self) -> Dict[str, Any]: # Changed return type value to Any
        if not self.opponents:
            return {'avg_vpip': 25.0, 'avg_pfr': 15.0, 'table_type': 'unknown_no_opponents', 'sample_size': 0}
            
        # Filter for opponents with a minimum number of hands seen for more reliable stats
        min_hands_for_stats = self.config.get_setting('opponent_tracker',{}).get('min_hands_for_table_stats', 10) if self.config else 10
        
        relevant_profiles = [p for p in self.opponents.values() if p.hands_seen_count >= min_hands_for_stats]
        
        if not relevant_profiles:
            return {'avg_vpip': 25.0, 'avg_pfr': 15.0, 'table_type': f'unknown_low_sample_opps (need >{min_hands_for_stats} hands)', 'sample_size': 0}
            
        vpips = [profile.get_vpip() for profile in relevant_profiles]
        pfrs = [profile.get_pfr() for profile in relevant_profiles]
        
        avg_vpip = sum(vpips) / len(vpips)
        avg_pfr = sum(pfrs) / len(pfrs)
        
        # Classify table type based on VPIP/PFR averages
        # These thresholds can be configured
        if avg_vpip < 22: table_type = 'tight'
        elif avg_vpip > 30: table_type = 'loose'
        else: table_type = 'normal'

        if avg_pfr < (avg_vpip * 0.4): table_type += '_passive'
        elif avg_pfr > (avg_vpip * 0.7): table_type += '_aggressive'
        else: table_type += '_moderate'
            
        return {
            'avg_vpip': avg_vpip,
            'avg_pfr': avg_pfr,
            'table_type': table_type,
            'sample_size': len(relevant_profiles),
            'profiles_considered': len(relevant_profiles)
        }
        
    def get_opponent_exploitative_adjustments(self, player_name: str, game_situation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggests exploitative adjustments against a specific opponent in a given situation.
        `game_situation` could include: our hand strength, position, street, pot odds, etc.
        """
        profile = self.opponents.get(player_name)
        if not profile or profile.hands_seen_count < self.config.get_setting('opponent_tracker',{}).get('min_hands_for_exploits', 20):
            return {"primary_adjust": "play_standard", "reason": "Not enough data or profile not found."}

        player_type = profile.classify_player_type()
        adjustments = {"player_type_identified": player_type}

        # Example adjustments based on player type
        if player_type == "tight_passive":
            adjustments["primary_adjust"] = "value_bet_thinner_bluff_more"
            adjustments["reason"] = "Tight passives fold often, call with medium hands. Can be bluffed, value bet thinner."
            adjustments["bluff_frequency_mod"] = "increase"
            adjustments["value_bet_range_mod"] = "widen_thin"
        elif player_type == "tight_aggressive":
            adjustments["primary_adjust"] = "play_solid_avoid_thin_calls"
            adjustments["reason"] = "TAGs are strong. Avoid marginal spots. Respect their aggression."
            adjustments["bluff_frequency_mod"] = "standard_or_decrease_oop"
            adjustments["call_vs_aggression_mod"] = "tighten"
        elif player_type == "loose_passive": # Calling station
            adjustments["primary_adjust"] = "value_bet_relentlessly_rarely_bluff"
            adjustments["reason"] = "Loose passives call too much. Maximize value, minimize bluffs."
            adjustments["bluff_frequency_mod"] = "decrease_significantly"
            adjustments["value_bet_range_mod"] = "widen_strong_medium"
            adjustments["bet_sizing_mod_value"] = "increase"
        elif player_type == "loose_aggressive": # LAG
            adjustments["primary_adjust"] = "trap_more_induce_bluffs_3bet_polarised"
            adjustments["reason"] = "LAGs are aggressive. Let them bluff, 3-bet/4-bet them with a polarized range."
            adjustments["bluff_catch_range_mod"] = "widen"
            adjustments["reraise_frequency_mod_vs_steal"] = "increase_polarized"
        elif player_type == "whale":
            adjustments["primary_adjust"] = "isolate_value_bet_heavily_no_fancy_plays"
            adjustments["reason"] = "Whales are very loose and passive. Isolate them, value bet very wide and for large sizes."
            adjustments["bluff_frequency_mod"] = "almost_never"
            adjustments["value_bet_range_mod"] = "widen_significantly"
            adjustments["bet_sizing_mod_value"] = "increase_significantly"
        elif player_type == "maniac":
            adjustments["primary_adjust"] = "play_tight_let_them_hang_themselves"
            adjustments["reason"] = "Maniacs overplay hands. Wait for strong hands, let them build the pot."
            adjustments["playing_range_mod"] = "tighten_significantly"
            adjustments["bluff_catch_range_mod"] = "widen_strong_medium"
        else: # unknown_low_sample or moderate types
            adjustments["primary_adjust"] = "play_standard_gather_data"
            adjustments["reason"] = f"Player type is {player_type}. More data needed or play standard."

        # Further refine based on specific stats like Fold to Cbet, Cbet%, etc.
        # Example: If player folds to flop c-bets > 70%
        flop_cbet_perc, flop_cbet_opps = profile.get_cbet_stat(FLOP) # This is their cbet stat, not fold to
        # Need fold_to_cbet stat from profile
        # if profile.get_fold_to_cbet_stat(FLOP)[0] > 70 and game_situation.get('street') == FLOP and game_situation.get('can_cbet'):
        #     adjustments["specific_action_advice"] = "C-bet frequently as a bluff."
        
        return adjustments

    def get_all_opponent_summaries(self) -> List[str]:
        """Returns a list of string summaries for all tracked opponents."""
        return [str(profile) for name, profile in self.opponents.items() if profile.hands_seen_count > 0]

# Example usage (for testing or integration)
if __name__ == '__main__':
    # Setup basic logging for testing this module
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__) # Create a logger instance for the test block
    
    test_config = {
        'opponent_tracker': {
            'max_hands_to_track_per_opponent': 50,
            'max_actions_to_store_per_hand': 15,
            'min_hands_for_table_stats': 5,
            'min_hands_for_exploits': 10
        }
    }
    tracker = OpponentTracker(config=test_config, logger_instance=logger)
    
    # --- Hand 1 ---
    hand_id_1 = "hand123"
    tracker.log_action(player_name="PlayerA", action_type="CALL", street=PREFLOP, position="BTN", amount=10, pot_size_before_action=15, hand_id=hand_id_1, players_in_hand_at_action=3)
    tracker.log_action(player_name="PlayerB", action_type="RAISE", street=PREFLOP, position="SB", amount=40, pot_size_before_action=25, hand_id=hand_id_1, players_in_hand_at_action=3)
    tracker.log_action(player_name="PlayerA", action_type="CALL", street=PREFLOP, position="BTN", amount=30, pot_size_before_action=65, hand_id=hand_id_1, players_in_hand_at_action=2)
    
    # Flop actions for Hand 1
    tracker.log_action(player_name="PlayerB", action_type="BET", street=FLOP, amount=50, pot_size_before_action=95, hand_id=hand_id_1, position="SB", players_in_hand_at_action=2)
    tracker.log_action(player_name="PlayerA", action_type="FOLD", street=FLOP, hand_id=hand_id_1, position="BTN", players_in_hand_at_action=2)

    # --- Hand 2 (Player A involved again) ---
    hand_id_2 = "hand124"
    tracker.log_action(player_name="PlayerA", action_type="RAISE", street=PREFLOP, position="CO", amount=25, pot_size_before_action=15, hand_id=hand_id_2, players_in_hand_at_action=4)
    tracker.log_action(player_name="PlayerC", action_type="CALL", street=PREFLOP, position="BTN", amount=25, pot_size_before_action=40, hand_id=hand_id_2, players_in_hand_at_action=2)

    # Flop actions for Hand 2
    tracker.log_action(player_name="PlayerA", action_type="BET", street=FLOP, amount=30, pot_size_before_action=65, hand_id=hand_id_2, position="CO", players_in_hand_at_action=2)
    tracker.log_action(player_name="PlayerC", action_type="CALL", street=FLOP, amount=30, pot_size_before_action=95, hand_id=hand_id_2, position="BTN", players_in_hand_at_action=2)

    # Turn actions for Hand 2
    tracker.log_action(player_name="PlayerA", action_type="CHECK", street=TURN, hand_id=hand_id_2, position="CO", players_in_hand_at_action=2)
    tracker.log_action(player_name="PlayerC", action_type="BET", street=TURN, amount=70, pot_size_before_action=125, hand_id=hand_id_2, position="BTN", players_in_hand_at_action=2)
    tracker.log_action(player_name="PlayerA", action_type="FOLD", street=TURN, hand_id=hand_id_2, position="CO", players_in_hand_at_action=2)


    logger.info("\n--- Opponent Summaries ---")
    for summary in tracker.get_all_opponent_summaries():
        logger.info(summary)

    logger.info("\n--- Table Dynamics ---")
    logger.info(tracker.get_table_dynamics())

    logger.info("\n--- Exploitative Adjustments for PlayerA ---")
    situation = {'street': FLOP, 'can_cbet': True} # Example situation
    logger.info(tracker.get_opponent_exploitative_adjustments("PlayerA", situation))
    
    logger.info("\n--- Player A Profile Details ---")
    profile_a = tracker.get_opponent_profile("PlayerA") # Corrected method name
    logger.info(f"Player A VPIP: {profile_a.get_vpip():.2f}%")
    logger.info(f"Player A PFR: {profile_a.get_pfr():.2f}%")
    logger.info(f"Player A Flop CBet: {profile_a.get_cbet_stat(FLOP)[0]:.2f}% ({profile_a.get_cbet_stat(FLOP)[1]} opps)")
    logger.info(f"Player A Hand Action History (first hand): {profile_a.hand_action_history[0] if profile_a.hand_action_history else 'None'}")
    logger.info(f"Player A Hand Action History (second hand): {profile_a.hand_action_history[1] if len(profile_a.hand_action_history) > 1 else 'None'}")

    logger.info("\n--- Player B Profile Details ---")
    profile_b = tracker.get_opponent_profile("PlayerB") # Corrected method name
    logger.info(f"Player B VPIP: {profile_b.get_vpip():.2f}%")
    logger.info(f"Player B PFR: {profile_b.get_pfr():.2f}%")
    logger.info(f"Player B Flop CBet: {profile_b.get_cbet_stat(FLOP)[0]:.2f}% ({profile_b.get_cbet_stat(FLOP)[1]} opps)")
    logger.info(f"Player B Hand Action History: {profile_b.hand_action_history[0] if profile_b.hand_action_history else 'None'}")
