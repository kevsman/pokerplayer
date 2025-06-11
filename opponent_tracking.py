# opponent_tracking.py
# Enhanced opponent modeling and tracking for poker bot

import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any # Added Any

logger = logging.getLogger(__name__)

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
    
    def __init__(self, player_name: str, max_hands_tracked: int = 100, max_actions_per_hand: int = 20): # Added max_actions_per_hand
        self.player_name = player_name
        self.max_hands_tracked = max_hands_tracked
        self.max_actions_per_hand = max_actions_per_hand # Store this
        
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
        if self.current_hand_id and self.current_hand_actions: # If there was a previous hand with actions
            # Store the completed hand's actions
            # Limit the number of actions stored per hand to avoid excessive memory use
            if len(self.current_hand_actions) > self.max_actions_per_hand:
                 logger.warning(f"Player {self.player_name}, Hand {self.current_hand_id}: Exceeded max_actions_per_hand ({len(self.current_hand_actions)} > {self.max_actions_per_hand}). Truncating.")
                 self.current_hand_actions = self.current_hand_actions[:self.max_actions_per_hand]

            self.hand_action_history.append({
                "hand_id": self.current_hand_id,
                "actions": list(self.current_hand_actions) # Store a copy
            })
        self.current_hand_actions = []
        self.current_hand_id = hand_id
        self.hands_seen_count += 1 # Increment when a new hand starts and player is involved

        # Reset per-hand flags (e.g., for C-bet opportunities)
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


    def log_action(self, action_type: str, street: str, amount: float = 0, pot_size_before_action: float = 0, 
                     position: Optional[str] = None, is_our_hero: bool = False, players_in_hand_at_action: int = 0):
        """
        Logs a single action taken by the opponent.
        This is the primary method for updating opponent statistics.
        """
        if not self.current_hand_id:
            logger.warning(f"Player {self.player_name}: Log_action called without current_hand_id. Action: {action_type} on {street}")
            # Potentially initialize a placeholder hand_id or queue action if this is valid
            return

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

        # --- PREFLOP Stats ---
        if street == PREFLOP:
            # This assumes player is dealt cards if an action is logged for them preflop
            # A more robust way would be to have an explicit "dealt_in" signal per hand
            if not hasattr(self, '_preflop_opportunity_counted_this_hand') or not self._preflop_opportunity_counted_this_hand:
                self.preflop_opportunities += 1
                self._preflop_opportunity_counted_this_hand = True # Flag to count only once per hand

            action_upper = action_type.upper()
            if action_upper in ["CALL", "BET", "RAISE"]:
                if not hasattr(self, '_vpip_counted_this_hand') or not self._vpip_counted_this_hand:
                    self.preflop_vpip_actions += 1
                    self._vpip_counted_this_hand = True # Count VPIP only once per hand
                if position:
                    self.position_stats[position]["vpip_hands"] += 1


            if action_upper in ["BET", "RAISE"]: # PFR includes open bets (limped pot) or raises
                if not hasattr(self, '_pfr_counted_this_hand') or not self._pfr_counted_this_hand:
                    self.preflop_pfr_actions += 1
                    self._pfr_counted_this_hand = True # Count PFR only once per hand
                    self.was_preflop_aggressor_this_hand = True
                if position:
                    self.position_stats[position]["pfr_hands"] += 1
                
                # Store bet sizing (as ratio to pot or BBs)
                # Example: if it's an open raise, amount / big_blind_amount
                # if it's a 3-bet, amount / previous_raise_amount
                # This needs more context from the game state (e.g. big blind, previous action)
                if pot_size_before_action > 0 and amount > 0 : # Basic bet sizing as % of pot
                     self.bet_sizes[PREFLOP][action_upper].append(amount / pot_size_before_action)


            if position:
                self.position_stats[position]["hands_dealt"] +=1 # Total hands seen from this position
                self.position_stats[position][f"{action_upper}_actions"] += 1


        # --- POSTFLOP Stats ---
        # This section needs significant expansion based on the detailed stats to track.
        # For example, C-betting, folding to C-bets, aggression per street.
        elif street in [FLOP, TURN, RIVER]:
            if street == FLOP and not self.saw_flop_this_hand:
                self.saw_flop_this_hand = True
                self.street_stats[FLOP]["saw_flop_count"] += 1
                if self.was_preflop_aggressor_this_hand:
                    self.cbet_opportunity_flop = True # Player was PFR and saw flop
                    self.street_stats[FLOP]["cbet_opportunities"] += 1
            
            action_upper = action_type.upper()
            self.street_stats[street][f"{action_upper}_count"] += 1
            self.street_stats[street]["total_actions_on_street"] += 1

            if amount > 0 and pot_size_before_action > 0:
                 self.bet_sizes[street][action_upper].append(amount / pot_size_before_action)

            # C-bet Made (Flop)
            if street == FLOP and self.cbet_opportunity_flop and action_upper in ["BET", "RAISE"]:
                self.street_stats[FLOP]["cbets_made"] += 1
                self.cbet_opportunity_flop = False # Action taken, opportunity consumed

            # Fold to Flop C-bet
            # Need to identify if the player is facing a C-bet.
            # This requires knowing who the C-bettor was (the PFR).
            # If facing_cbet_flop and action_upper == "FOLD":
            #    self.street_stats[FLOP]["fold_to_cbet_count"] += 1

            # Aggression Frequency (AFq) on this street
            # AFq = (Bets + Raises) / (Bets + Raises + Calls + Folds) * 100
            # This is typically calculated at the end of a hand or session for overall AFq.
            # Per-street AFq can also be tracked.
            # For now, just count actions, calculation can be done in getter methods.

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
    Manages multiple opponent profiles and provides analysis.
    """
    
    def __init__(self, config=None, logger_instance=None): # Renamed logger to logger_instance
        self.opponents: Dict[str, OpponentProfile] = {}
        self.config = config 
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__) 
        self.current_hand_id_for_tracker: Optional[str] = None


    def get_or_create_profile(self, player_name: str) -> OpponentProfile:
        if player_name not in self.opponents:
            max_hands = self.config.get('opponent_tracker',{}).get('max_hands_to_track_per_opponent', 100) if self.config else 100
            max_actions = self.config.get('opponent_tracker',{}).get('max_actions_to_store_per_hand', 20) if self.config else 20
            self.opponents[player_name] = OpponentProfile(player_name, max_hands_tracked=max_hands, max_actions_per_hand=max_actions)
            self.logger.info(f"Created new profile for opponent: {player_name}")
        return self.opponents[player_name]
        
    def log_action(self, player_name: str, action_type: str, street: str, 
                             position: Optional[str] = None, bet_amount: float = 0, # Renamed amount to bet_amount
                             pot_size_before_action: float = 0, # Added pot_size_before_action
                             hand_id: Optional[str] = None,
                             is_our_hero: bool = False, # Added is_our_hero
                             players_in_hand_at_action: int = 0): # Added players_in_hand_at_action
        
        if not hand_id:
            self.logger.warning(f"OpponentTracker.log_action called for {player_name} without hand_id. Action: {action_type}. Discarding.")
            return

        profile = self.get_or_create_profile(player_name)
        
        # Check if it's a new hand for this player profile
        if hand_id != profile.current_hand_id:
            profile.new_hand(hand_id) # This also updates profile.current_hand_id

        # If it's a new hand for the tracker overall (first action of a new hand_id seen by tracker)
        if hand_id != self.current_hand_id_for_tracker:
            self.current_hand_id_for_tracker = hand_id
            # Potentially reset/update other tracker-level per-hand states if any

        self.logger.debug(
            f"Tracker logging action for {player_name} (Hero: {is_our_hero}): Hand ID {hand_id}, Street: {street}, "
            f"Action: {action_type}, Pos: {position}, Amt: {bet_amount}, PotBefore: {pot_size_before_action}, PlayersInHand: {players_in_hand_at_action}"
        )

        profile.log_action(
            action_type=action_type, 
            street=street, 
            amount=bet_amount, 
            pot_size_before_action=pot_size_before_action,
            position=position,
            is_our_hero=is_our_hero,
            players_in_hand_at_action=players_in_hand_at_action
        )
            
    def get_table_dynamics(self) -> Dict[str, Any]: # Changed return type value to Any
        if not self.opponents:
            return {'avg_vpip': 25.0, 'avg_pfr': 15.0, 'table_type': 'unknown_no_opponents', 'sample_size': 0}
            
        # Filter for opponents with a minimum number of hands seen for more reliable stats
        min_hands_for_stats = self.config.get('opponent_tracker',{}).get('min_hands_for_table_stats', 10) if self.config else 10
        
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
        if not profile or profile.hands_seen_count < self.config.get('opponent_tracker',{}).get('min_hands_for_exploits', 20):
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
    tracker.log_action(player_name="PlayerA", action_type="CALL", street=PREFLOP, position="BTN", bet_amount=10, pot_size_before_action=15, hand_id=hand_id_1, players_in_hand_at_action=3)
    tracker.log_action(player_name="PlayerB", action_type="RAISE", street=PREFLOP, position="SB", bet_amount=40, pot_size_before_action=25, hand_id=hand_id_1, players_in_hand_at_action=3)
    tracker.log_action(player_name="PlayerA", action_type="CALL", street=PREFLOP, position="BTN", bet_amount=30, pot_size_before_action=65, hand_id=hand_id_1, players_in_hand_at_action=2)
    
    # Flop actions for Hand 1
    tracker.log_action(player_name="PlayerB", action_type="BET", street=FLOP, bet_amount=50, pot_size_before_action=95, hand_id=hand_id_1, position="SB", players_in_hand_at_action=2)
    tracker.log_action(player_name="PlayerA", action_type="FOLD", street=FLOP, hand_id=hand_id_1, position="BTN", players_in_hand_at_action=2)

    # --- Hand 2 (Player A involved again) ---
    hand_id_2 = "hand124"
    tracker.log_action(player_name="PlayerA", action_type="RAISE", street=PREFLOP, position="CO", bet_amount=25, pot_size_before_action=15, hand_id=hand_id_2, players_in_hand_at_action=4)
    tracker.log_action(player_name="PlayerC", action_type="CALL", street=PREFLOP, position="BTN", bet_amount=25, pot_size_before_action=40, hand_id=hand_id_2, players_in_hand_at_action=2)

    # Flop actions for Hand 2
    tracker.log_action(player_name="PlayerA", action_type="BET", street=FLOP, bet_amount=30, pot_size_before_action=65, hand_id=hand_id_2, position="CO", players_in_hand_at_action=2)
    tracker.log_action(player_name="PlayerC", action_type="CALL", street=FLOP, bet_amount=30, pot_size_before_action=95, hand_id=hand_id_2, position="BTN", players_in_hand_at_action=2)

    # Turn actions for Hand 2
    tracker.log_action(player_name="PlayerA", action_type="CHECK", street=TURN, hand_id=hand_id_2, position="CO", players_in_hand_at_action=2)
    tracker.log_action(player_name="PlayerC", action_type="BET", street=TURN, bet_amount=70, pot_size_before_action=125, hand_id=hand_id_2, position="BTN", players_in_hand_at_action=2)
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
    profile_a = tracker.get_or_create_profile("PlayerA")
    logger.info(f"Player A VPIP: {profile_a.get_vpip():.2f}%")
    logger.info(f"Player A PFR: {profile_a.get_pfr():.2f}%")
    logger.info(f"Player A Flop CBet: {profile_a.get_cbet_stat(FLOP)[0]:.2f}% ({profile_a.get_cbet_stat(FLOP)[1]} opps)")
    logger.info(f"Player A Hand Action History (first hand): {profile_a.hand_action_history[0] if profile_a.hand_action_history else 'None'}")
    logger.info(f"Player A Hand Action History (second hand): {profile_a.hand_action_history[1] if len(profile_a.hand_action_history) > 1 else 'None'}")

    logger.info("\n--- Player B Profile Details ---")
    profile_b = tracker.get_or_create_profile("PlayerB")
    logger.info(f"Player B VPIP: {profile_b.get_vpip():.2f}%")
    logger.info(f"Player B PFR: {profile_b.get_pfr():.2f}%")
    logger.info(f"Player B Flop CBet: {profile_b.get_cbet_stat(FLOP)[0]:.2f}% ({profile_b.get_cbet_stat(FLOP)[1]} opps)")
    logger.info(f"Player B Hand Action History: {profile_b.hand_action_history[0] if profile_b.hand_action_history else 'None'}")
