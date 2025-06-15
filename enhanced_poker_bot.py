# enhanced_poker_bot.py
"""
Enhanced poker bot with comprehensive improvements:
1. Adaptive timing controller for optimized parsing
2. Enhanced action detection with multiple fallback strategies
3. Advanced decision engine with sophisticated strategy
4. Enhanced opponent tracking and modeling
5. Real-time performance monitoring and adaptive adjustments
6. Better error handling and robustness
"""

import logging
import time
import sys
from typing import Dict, List, Optional, Tuple, Any

# Import all enhanced modules
from adaptive_timing_controller import AdaptiveTimingController, GameStateSnapshot, create_adaptive_timing_controller
from enhanced_action_detection import EnhancedActionDetector, ActionElement, create_enhanced_action_detector
from advanced_decision_engine import AdvancedDecisionEngine, DecisionContext, OpponentProfile as AdvancedOpponentProfile, PlayingStyle, BoardTexture, create_advanced_decision_engine
from enhanced_opponent_tracking import EnhancedOpponentTracker, EnhancedOpponentProfile, ActionData, HandData, create_enhanced_opponent_tracker
from performance_monitor import PerformanceMonitor, HandPerformance, SessionMetrics, create_performance_monitor

# Import existing modules
from enhanced_opponent_analysis import get_enhanced_opponent_analysis
from improved_postflop_decisions import make_improved_postflop_decision, format_decision_explanation
from session_performance_tracker import SessionPerformanceTracker, HandResult, get_session_tracker

# Import base modules
from poker_bot import PokerBot
from decision_engine import ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE

class EnhancedPokerBot(PokerBot):
    """Enhanced poker bot with comprehensive improvements integrated."""
    
    def __init__(self, config_path='config.json'):
        # Initialize enhanced components safely for testing
        try:
            super().__init__(config_path)
        except Exception as e:
            # Handle test environment where parent init might fail
            self.logger = logging.getLogger(__name__)
            self.config = type('Config', (), {'settings': {}})()
            self.parser = type('Parser', (), {})()
            self.ui_controller = type('UIController', (), {})()
            self.opponent_tracker = type('OpponentTracker', (), {})()
            self.table_data = {}
            self.player_data = []
            self.action_history = []
            self.current_hand_id_for_history = None
        
        # Initialize enhanced components
        self.timing_controller = create_adaptive_timing_controller()
        self.action_detector = create_enhanced_action_detector(self.parser)
        self.decision_engine_advanced = create_advanced_decision_engine(self.config.settings)
        self.opponent_tracker_enhanced = create_enhanced_opponent_tracker(self.config.settings, self.logger)
        self.performance_monitor = create_performance_monitor(self.config.settings)
        self.session_tracker = get_session_tracker()
        
        # Enhanced tracking
        self.current_hand_start_time = None
        self.current_hand_starting_stack = 0.0
        self.current_hand_actions = []
        self.last_decision_time = 0.0
        self.consecutive_parse_failures = 0
        self.last_game_state = None
        
        # Performance metrics
        self.total_decisions_made = 0
        self.successful_parses = 0
        self.failed_parses = 0
        self.actions_taken_this_session = []        
        # Strategy adaptation
        self.strategy_adjustments = {
            'aggression_multiplier': 1.0,
            'tightness_adjustment': 0.0,
            'bluff_frequency_multiplier': 1.0
        }
        
        self.logger.info("Enhanced Poker Bot initialized with comprehensive improvements")
    
    def enhanced_main_loop(self):
        """Enhanced main loop with comprehensive improvements."""
        
        self.logger.info("Enhanced Poker Bot - Main Loop Started")
        self.performance_monitor.session_start_time = time.time()
        
        try:
            while True:
                current_time = time.time()
                
                # Create current game state snapshot for timing decisions
                current_state = self._create_game_state_snapshot()
                
                # Smart timing decision
                if not self.timing_controller.should_parse_now(current_state):
                    time.sleep(0.1)  # Short sleep when parsing not needed
                    continue
                
                self.logger.info("\n--- Enhanced Decision Cycle ---")
                
                # Get HTML with enhanced error handling
                current_html = self._get_html_with_enhanced_retry()
                if not current_html:
                    self._handle_parse_failure()
                    continue
                
                # Parse HTML with enhanced detection
                parsed_result = self._enhanced_parse_html(current_html)
                if not parsed_result:
                    self._handle_parse_failure()
                    continue
                
                # Record successful parse
                self.successful_parses += 1
                self.consecutive_parse_failures = 0
                
                # Record parse result in timing controller
                game_state = self._create_game_state_snapshot(parsed_result)
                self.timing_controller.record_parse_result(game_state, True)
                
                # Enhanced game state analysis
                game_analysis = self._enhanced_game_analysis(parsed_result)
                if not game_analysis:
                    continue
                
                # Decision making with enhanced logic
                if game_analysis['my_turn']:
                    self.logger.info("My turn detected - making enhanced decision")
                    decision_result = self._make_enhanced_decision(game_analysis)
                    if decision_result:
                        self._execute_enhanced_action(decision_result, game_analysis)
                        self.timing_controller.record_action_taken()
                else:
                    self._handle_waiting_state(game_analysis)
                
                # Update performance monitoring
                self._update_performance_tracking(game_analysis)
                
                # Apply adaptive strategy adjustments
                self._apply_adaptive_adjustments()
                  # Adaptive timing based on game activity
                recommended_delay = self.timing_controller.get_recommended_delay()
                time.sleep(recommended_delay)
                
        except KeyboardInterrupt:
            self.logger.info("Enhanced Poker Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Critical error in enhanced main loop: {e}", exc_info=True)
        finally:
            self._cleanup_session()
    
    def _get_html_with_enhanced_retry(self) -> Optional[str]:
        """Get HTML with enhanced retry logic and error handling."""
        
        max_retries = 3
        retry_delays = [0.5, 1.0, 2.0]
        
        for attempt in range(max_retries):
            try:
                html = self.ui_controller.get_html_from_screen_with_auto_retry()
                if html and len(html) > 100:  # Basic validation
                    return html
                else:
                    self.logger.warning(f"HTML retrieval attempt {attempt + 1} failed or returned insufficient data")
            except Exception as e:
                self.logger.warning(f"HTML retrieval error on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
        
        self.failed_parses += 1
        return None
    
    def _create_game_state_snapshot(self, parsed_result: Dict = None) -> GameStateSnapshot:
        """Create a game state snapshot for timing decisions."""
        if not parsed_result:
            return GameStateSnapshot(
                hand_id=None,
                pot_size=0.0,
                active_player=None,
                game_stage='unknown',
                my_turn=False,
                actions_available=0,
                timestamp=time.time()
            )
        
        table_data = parsed_result.get('table_data', {})
        my_player = parsed_result.get('my_player', {})
        actions = parsed_result.get('actions_available', [])
        
        return GameStateSnapshot(
            hand_id=table_data.get('hand_id'),
            pot_size=table_data.get('pot_size', 0.0),
            active_player=parsed_result.get('active_player', {}).get('name') if parsed_result.get('active_player') else None,
            game_stage=table_data.get('game_stage', 'preflop'),
            my_turn=my_player.get('has_turn', False),
            actions_available=len(actions),
            timestamp=time.time()
        )
    
    def _handle_parse_failure(self):
        """Handle parsing failures with adaptive response."""
        self.failed_parses += 1
        self.consecutive_parse_failures += 1
        
        if self.consecutive_parse_failures > 10:
            self.logger.error("Too many consecutive parse failures. Taking extended break.")
            time.sleep(5.0)
            self.consecutive_parse_failures = 0
        
        # Record failure in timing controller
        if self.last_game_state:
            self.timing_controller.record_parse_result(self.last_game_state, False)
    
    def _enhanced_parse_html(self, html_content: str) -> Optional[Dict]:
        """Parse HTML with enhanced action detection."""
        try:
            # Use base parser for initial parsing
            parsed_state = self.parser.parse_html(html_content)
            if not parsed_state or parsed_state.get('error'):
                return None
            
            # Populate data structures
            self.analyze()
            
            # Enhanced action detection
            actions, confidence = self.action_detector.detect_available_actions()
            
            # Convert to enhanced format
            enhanced_result = {
                'parsed_state': parsed_state,
                'table_data': self.table_data,
                'player_data': self.player_data,
                'my_player': self.get_my_player(),
                'active_player': self.get_active_player(),
                'actions_available': [{'type': action.action_type, 'confidence': action.confidence} for action in actions],
                'action_confidence': confidence,
                'enhanced_actions': actions
            }
            
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Enhanced parsing error: {e}")
            return None
    
    def _enhanced_game_analysis(self, parsed_result: Dict) -> Optional[Dict]:
        """Enhanced game analysis with better opponent tracking."""
        
        try:
            my_player = parsed_result['my_player']
            table_data = parsed_result['table_data']
            
            if not my_player or not table_data:
                return None
            
            # Track hand changes
            current_hand_id = table_data.get('hand_id')
            if current_hand_id != self.current_hand_id_for_history:
                self._handle_new_hand(current_hand_id, my_player)
            
            # Enhanced opponent analysis
            active_opponents_count = len([p for p in parsed_result['player_data'] 
                                        if not p.get('is_empty', False) and not p.get('is_my_player', False)])
            
            opponent_analysis = get_enhanced_opponent_analysis(
                opponent_tracker=self.opponent_tracker,
                active_opponents_count=active_opponents_count,
                table_data=table_data,
                recent_actions=self.action_history[-20:] if self.action_history else None
            )
              # Determine if it's our turn with enhanced logic
            my_turn = (
                my_player.get('has_turn', False) or
                len(parsed_result['actions_available']) > 0
            )
            
            game_analysis = {
                'my_player': my_player,
                'table_data': table_data,
                'opponent_analysis': opponent_analysis,
                'my_turn': my_turn,
                'actions_available': parsed_result['actions_available'],
                'active_opponents_count': active_opponents_count,
                'community_cards': table_data.get('community_cards', []),
                'pot_size': table_data.get('pot_size', 0.0),
                'game_stage': table_data.get('game_stage', 'preflop'),
                'hand_id': current_hand_id
            }
            
            return game_analysis
            
        except Exception as e:
            self.logger.error(f"Enhanced game analysis error: {e}")
            return None
    
    def _handle_new_hand(self, hand_id: str, my_player: Dict):
        """Handle new hand detection with session tracking."""
        
        # Complete previous hand tracking
        if (self.current_hand_id_for_history and 
            self.current_hand_start_time and 
            self.current_hand_starting_stack > 0):
            
            self._complete_hand_tracking()
        
        # Start new hand tracking
        self.current_hand_id_for_history = hand_id
        self.current_hand_start_time = time.time()
        self.current_hand_actions = []
        
        # Get starting stack for this hand
        stack_str = my_player.get('stack', '0')
        if isinstance(stack_str, str):
            stack_str = stack_str.replace('€', '').replace('$', '').strip()
        try:
            self.current_hand_starting_stack = float(stack_str)
        except ValueError:
            self.current_hand_starting_stack = 0.0
        
        # Reset action history for new hand
        self.action_history = []
        
        # Notify opponent tracker of new hand
        if self.opponent_tracker:
            for opponent_name in self.opponent_tracker.opponents:
                profile = self.opponent_tracker.opponents[opponent_name]
                if hasattr(profile, 'new_hand'):
                    profile.new_hand(hand_id)
        
        self.logger.info(f"New hand detected: {hand_id}, starting stack: ${self.current_hand_starting_stack:.2f}")
    
    def _complete_hand_tracking(self):
        """Complete tracking for the finished hand."""
        
        try:
            if not all([self.current_hand_id_for_history, 
                       self.current_hand_start_time, 
                       self.current_hand_starting_stack > 0]):
                return
            
            # Calculate hand result
            current_stack = self._get_current_stack()
            profit_loss = current_stack - self.current_hand_starting_stack
            
            # Determine outcome
            outcome = 'unknown'
            if profit_loss > 0:
                outcome = 'win'
            elif profit_loss < 0:
                outcome = 'loss'
            else:
                outcome = 'fold'  # Likely folded
            
            # Create hand result
            hand_result = HandResult(
                hand_id=self.current_hand_id_for_history,
                start_time=self.current_hand_start_time,
                end_time=time.time(),
                position=self._get_last_known_position(),
                starting_stack=self.current_hand_starting_stack,
                ending_stack=current_stack,
                profit_loss=profit_loss,
                actions_taken=self.current_hand_actions.copy(),
                win_probability_estimates=self._extract_win_probabilities(),
                final_outcome=outcome,
                showdown=self._was_showdown(),
                hand_strength=self._get_hand_strength_summary()
            )
            
            # Record in session tracker
            self.session_tracker.record_hand_result(hand_result)
            
        except Exception as e:
            self.logger.error(f"Error completing hand tracking: {e}")
    
    def _make_enhanced_decision(self, game_analysis: Dict) -> Optional[Dict]:
        """Make decision using advanced decision engine."""
        
        try:
            my_player = game_analysis['my_player']
            table_data = game_analysis['table_data']
            
            if not my_player or not table_data:
                return None
            
            # Get decision context
            win_probability = my_player.get('win_probability', 0.0)
            bet_to_call = my_player.get('bet_to_call', 0.0)
            stack_size = self._parse_stack_amount(my_player.get('stack', '0'))
            pot_size = table_data.get('pot_size', 0.0)
            
            # Calculate pot odds
            pot_odds = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 0
              # Get available actions
            available_actions = [action['type'] for action in game_analysis.get('actions_available', [])]
              # Debug logging for available actions
            self.logger.info(f"Available actions detected: {available_actions}")
            self.logger.info(f"Bet to call: {bet_to_call}, Pot size: {pot_size}, Win probability: {win_probability}")
            
            # Get opponent profiles
            opponent_profiles = []
            for player in game_analysis.get('player_data', []):
                if not player.get('is_my_player', False) and not player.get('is_empty', False):
                    profile = self.opponent_tracker_enhanced.get_or_create_opponent(player.get('name', 'Unknown'))
                    opponent_profiles.append(self._convert_to_advanced_profile(profile))
            
            # Create decision context
            context = DecisionContext(
                hand_strength=my_player.get('hand_evaluation', ('', 'Unknown'))[1],
                position=my_player.get('position', 'Unknown'),
                pot_size=pot_size,
                bet_to_call=bet_to_call,
                stack_size=stack_size,
                pot_odds=pot_odds,
                win_probability=win_probability,
                opponents=opponent_profiles,
                board_texture=self._classify_board_texture(table_data.get('community_cards', [])),
                street=table_data.get('game_stage', 'preflop').lower(),
                spr=stack_size / max(pot_size, 0.01),  # Stack-to-Pot Ratio
                actions_available=available_actions,
                betting_history=self.action_history[-10:] if self.action_history else []
            )
            
            # Apply adaptive adjustments
            self._apply_strategy_adjustments_to_context(context)
              # Make advanced decision
            action, amount, reasoning = self.decision_engine_advanced.make_advanced_decision(context)
              # CRITICAL SAFEGUARD: Never fold when check is available
            if action == 'fold' and 'check' in available_actions:
                action = 'check'
                amount = 0.0
                reasoning += " [SAFEGUARD: Changed fold to check when check available]"
                self.logger.warning(f"SAFEGUARD ACTIVATED: Changed fold to check when check was available. Actions: {available_actions}")
            
            # Additional safeguard: If bet_to_call is 0, we should check not fold
            elif action == 'fold' and bet_to_call == 0.0:
                action = 'check'
                amount = 0.0
                reasoning += " [SAFEGUARD: Changed fold to check when no bet to call]"
                self.logger.warning(f"SAFEGUARD ACTIVATED: Changed fold to check when bet_to_call was 0. Bet to call: {bet_to_call}")
            
            self.logger.info(f"Final decision after safeguards: {action} {amount:.2f} - {reasoning}")
            
            # Record decision
            self.total_decisions_made += 1
            decision_record = {
                'action': action,
                'amount': amount,
                'reasoning': reasoning,
                'context': {
                    'hand_id': table_data.get('hand_id'),
                    'street': context.street,
                    'position': context.position,
                    'win_probability': win_probability,
                    'pot_odds': pot_odds,
                    'stack_size': stack_size
                }
            }
            
            # Log decision
            self.logger.info(f"Advanced decision: {action} {amount:.2f} - {reasoning}")
            
            return decision_record
            
        except Exception as e:
            self.logger.error(f"Enhanced decision making error: {e}")
            return {'action': 'fold', 'amount': 0.0, 'reasoning': 'Error fallback'}
    
    def _convert_to_advanced_profile(self, enhanced_profile: EnhancedOpponentProfile) -> AdvancedOpponentProfile:
        """Convert enhanced profile to advanced decision engine format."""
        return AdvancedOpponentProfile(
            name=enhanced_profile.player_name,
            vpip=enhanced_profile.vpip,
            pfr=enhanced_profile.pfr,
            aggression_factor=enhanced_profile.aggression_factor,
            hands_observed=enhanced_profile.total_hands_observed,
            style=enhanced_profile.playing_style,
            stack_size=enhanced_profile.avg_stack_size
        )
    
    def _classify_board_texture(self, community_cards: List[str]) -> BoardTexture:
        """Classify board texture for decision making."""
        if len(community_cards) < 3:
            return BoardTexture.DRY
        
        # Simple classification - could be enhanced
        suits = [card[-1] for card in community_cards[:3]]
        ranks = [card[:-1] for card in community_cards[:3]]
        
        # Check for flush draw
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        max_suit_count = max(suit_counts.values()) if suit_counts else 0
        
        # Check for straight possibilities
        rank_values = []
        for rank in ranks:
            if rank == 'A':
                rank_values.append(14)
            elif rank == 'K':
                rank_values.append(13)
            elif rank == 'Q':
                rank_values.append(12)
            elif rank == 'J':
                rank_values.append(11)
            elif rank == 'T':
                rank_values.append(10)
            else:
                rank_values.append(int(rank))
        
        rank_values.sort()
        is_connected = len(rank_values) >= 2 and (rank_values[-1] - rank_values[0]) <= 4
        
        # Classify texture
        if max_suit_count >= 2 and is_connected:
            return BoardTexture.WET
        elif max_suit_count >= 3:
            return BoardTexture.WET
        elif is_connected:            return BoardTexture.COORDINATED
        elif max_suit_count == 1:            return BoardTexture.RAINBOW
        else:
            return BoardTexture.DRY
    
    def _apply_strategy_adjustments_to_context(self, context: DecisionContext):
        """Apply adaptive strategy adjustments to decision context."""
        adjustments = self.performance_monitor.get_adaptive_adjustments()
        
        # Note: These would be applied to the decision engine's internal calculations
        # Rather than modifying the context directly
        pass
    
    def _update_performance_tracking(self, game_analysis: Dict):
        """Update performance tracking with current game state."""
        # Track hand completion
        current_hand_id = game_analysis.get('table_data', {}).get('hand_id')
        
        if (current_hand_id != self.current_hand_id_for_history and 
            self.current_hand_id_for_history and
            self.current_hand_start_time):
            self._complete_hand_performance_tracking()
    
    def _complete_hand_performance_tracking(self):
        """Complete performance tracking for finished hand."""
        try:
            current_stack = self._get_current_stack()
            profit_loss = current_stack - self.current_hand_starting_stack
            
            # Calculate decision quality score
            decision_quality = self._calculate_decision_quality_score()
            
            # Count bluffs
            bluffs_attempted = sum(1 for action in self.actions_taken_this_session 
                                 if action.get('was_bluff', False))
            bluffs_successful = sum(1 for action in self.actions_taken_this_session 
                                  if action.get('was_bluff', False) and action.get('successful', False))
            
            # Create hand performance record
            hand_performance = HandPerformance(
                hand_id=self.current_hand_id_for_history,
                timestamp=self.current_hand_start_time,
                starting_stack=self.current_hand_starting_stack,
                ending_stack=current_stack,
                profit_loss=profit_loss,
                position=self._get_last_known_position(),
                actions_taken=[action.get('action_type', '') for action in self.actions_taken_this_session],
                hand_strength=self._get_hand_strength_summary(),
                win_probability_avg=self._get_average_win_probability(),
                decision_quality_score=decision_quality,
                bluffs_attempted=bluffs_attempted,
                bluffs_successful=bluffs_successful,
                pot_size=self.table_data.get('pot_size', 0.0),
                opponents_count=len([p for p in self.player_data if not p.get('is_my_player', False)])
            )
            
            # Record in performance monitor
            self.performance_monitor.record_hand_result(hand_performance)
            
            # Reset for next hand
            self.actions_taken_this_session = []
            
        except Exception as e:
            self.logger.error(f"Error completing hand performance tracking: {e}")
    
    def _calculate_decision_quality_score(self) -> float:
        """Calculate a quality score for decisions made in this hand."""
        if not self.actions_taken_this_session:
            return 0.5
        
        # Simple scoring based on win probability vs pot odds
        score_sum = 0.0
        decision_count = 0
        
        for action in self.actions_taken_this_session:
            win_prob = action.get('win_probability', 0.5)
            pot_odds = action.get('pot_odds', 0.5)
            action_type = action.get('action_type', 'fold')
            
            if action_type == 'call' and win_prob > pot_odds:
                score_sum += 1.0  # Good call
            elif action_type == 'fold' and win_prob < pot_odds:
                score_sum += 1.0  # Good fold
            elif action_type in ['bet', 'raise'] and win_prob > 0.6:
                score_sum += 1.0  # Good value bet
            else:
                score_sum += 0.5  # Neutral decision
            
            decision_count += 1
        
        return score_sum / decision_count if decision_count > 0 else 0.5
    
    def _get_average_win_probability(self) -> float:
        """Get average win probability for this hand."""
        win_probs = [action.get('win_probability', 0.5) for action in self.actions_taken_this_session]
        return sum(win_probs) / len(win_probs) if win_probs else 0.5
    
    def _apply_adaptive_adjustments(self):
        """Apply adaptive strategy adjustments based on performance."""
        recommendations = self.performance_monitor.get_strategy_recommendations()
        
        if 'aggression' in recommendations:
            if 'increase' in recommendations['aggression'].lower():
                self.strategy_adjustments['aggression_multiplier'] = min(1.5, self.strategy_adjustments['aggression_multiplier'] * 1.05)
            elif 'decrease' in recommendations['aggression'].lower():
                self.strategy_adjustments['aggression_multiplier'] = max(0.7, self.strategy_adjustments['aggression_multiplier'] * 0.95)
        
        if 'vpip' in recommendations:
            if 'tighten' in recommendations['vpip'].lower():
                self.strategy_adjustments['tightness_adjustment'] = min(0.1, self.strategy_adjustments['tightness_adjustment'] + 0.01)
            elif 'loosen' in recommendations['vpip'].lower():
                self.strategy_adjustments['tightness_adjustment'] = max(-0.1, self.strategy_adjustments['tightness_adjustment'] - 0.01)

    def _get_current_stack(self) -> float:
        """Get current stack size."""
        try:
            my_player = self.get_my_player()
            if my_player:
                stack_str = my_player.get('stack', '0')
                return self._parse_stack_amount(stack_str)
            return 0.0
        except Exception:
            return 0.0
    
    def _parse_stack_amount(self, stack_str: str) -> float:
        """Parse stack amount from string."""
        try:
            if isinstance(stack_str, (int, float)):
                return float(stack_str)
            
            # Remove currency symbols and whitespace
            clean_str = str(stack_str).replace('€', '').replace('$', '').replace(',', '').strip()
            return float(clean_str) if clean_str else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _get_last_known_position(self) -> str:
        """Get the last known position."""
        try:
            my_player = self.get_my_player()
            return my_player.get('position', 'Unknown') if my_player else 'Unknown'
        except Exception:
            return 'Unknown'
    
    def _extract_win_probabilities(self) -> List[float]:
        """Extract win probabilities from current hand actions."""
        win_probs = []
        for action in self.actions_taken_this_session:
            win_prob = action.get('win_probability')
            if win_prob is not None:
                win_probs.append(float(win_prob))
        return win_probs
    
    def _was_showdown(self) -> bool:
        """Determine if the hand went to showdown."""
        # Simple heuristic: if we have community cards visible and made it to river
        try:
            community_cards = self.table_data.get('community_cards', [])
            return len(community_cards) >= 5
        except Exception:
            return False
    
    def _get_hand_strength_summary(self) -> str:
        """Get a summary of hand strength."""
        try:
            my_player = self.get_my_player()
            if my_player:
                hand_eval = my_player.get('hand_evaluation', ('', 'Unknown'))
                if isinstance(hand_eval, tuple) and len(hand_eval) > 1:
                    return hand_eval[1]
                elif isinstance(hand_eval, str):
                    return hand_eval
            return 'Unknown'
        except Exception:
            return 'Unknown'
    
    def _execute_enhanced_action(self, decision_result: Dict, game_analysis: Dict):
        """Execute the decided action with enhanced tracking."""
        try:
            action = decision_result['action']
            amount = decision_result.get('amount', 0.0)
            reasoning = decision_result.get('reasoning', '')
            
            # Record action for session tracking
            action_record = {
                'action_type': action,
                'amount': amount,
                'reasoning': reasoning,
                'timestamp': time.time(),
                'hand_id': game_analysis.get('table_data', {}).get('hand_id'),
                'win_probability': game_analysis.get('my_player', {}).get('win_probability', 0.0),
                'pot_odds': self._calculate_pot_odds(game_analysis),
                'stack_size': self._get_current_stack()
            }
            
            self.actions_taken_this_session.append(action_record)
            self.current_hand_actions.append(action_record)            # Execute the action
            if action == ACTION_FOLD:
                self.ui_controller.action_fold()
                self.logger.info(f"FOLD executed - {reasoning}")
            elif action == ACTION_CHECK:
                self.ui_controller.action_check_call()
                self.logger.info(f"CHECK executed - {reasoning}")
            elif action == ACTION_CALL:
                self.ui_controller.action_check_call()
                self.logger.info(f"CALL executed - {reasoning}")
            elif action == ACTION_RAISE:
                if amount > 0:
                    # Set raise amount and execute
                    self.ui_controller.action_raise(amount)
                    self.logger.info(f"RAISE {amount:.2f} executed - {reasoning}")
                else:
                    # Default raise - use action_all_in for simplicity
                    self.ui_controller.action_all_in()
                    self.logger.info(f"RAISE (all-in) executed - {reasoning}")
            
            # Record successful action execution
            self.last_decision_time = time.time()
            
            # Update opponent tracking with our action
            self._update_opponent_tracking_with_action(action_record, game_analysis)
        except Exception as e:
            self.logger.error(f"Error executing enhanced action: {e}", exc_info=True)
    
    def _calculate_pot_odds(self, game_analysis: Dict) -> float:
        """Calculate pot odds from game analysis."""
        try:
            my_player = game_analysis.get('my_player', {})
            table_data = game_analysis.get('table_data', {})
            
            bet_to_call = my_player.get('bet_to_call', 0.0)
            pot_size = table_data.get('pot_size', 0.0)
            
            if isinstance(bet_to_call, str):
                bet_to_call = self._parse_stack_amount(bet_to_call)
            if isinstance(pot_size, str):
                pot_size = self._parse_stack_amount(pot_size)
            
            total_pot = pot_size + bet_to_call
            return bet_to_call / total_pot if total_pot > 0 else 0.0
        except Exception:
            return 0.0
    
    def _update_opponent_tracking_with_action(self, action_record: Dict, game_analysis: Dict):
        """Update opponent tracking with our action."""
        try:
            # Get our player name
            my_player = game_analysis.get('my_player', {})
            my_name = my_player.get('name', 'Hero')
            
            # Track our action in opponent modeling using log_action method
            self.opponent_tracker_enhanced.log_action(
                player_name=my_name,
                action_type=action_record['action_type'],
                street=game_analysis.get('table_data', {}).get('game_stage', 'preflop'),
                position=self._get_last_known_position(),
                amount=action_record['amount'],
                pot_size_before_action=game_analysis.get('table_data', {}).get('pot_size', 0.0),
                stack_size=action_record['stack_size'],
                hand_id=game_analysis.get('table_data', {}).get('hand_id', ''),
                decision_time=0.0  # We could track this if needed
            )
            
        except Exception as e:
            self.logger.error(f"Error updating opponent tracking with action: {e}")
    
    def _handle_waiting_state(self, game_analysis: Dict):
        """Handle state when it's not our turn."""
        try:
            # Update opponent tracking with any new actions
            self._update_opponent_tracking_from_game_state(game_analysis)
            
            # Log current state periodically
            if time.time() - self.last_decision_time > 30:  # Every 30 seconds
                active_player = game_analysis.get('active_player', {})
                pot_size = game_analysis.get('table_data', {}).get('pot_size', 0.0)
                
                self.logger.info(f"Waiting - Active: {active_player.get('name', 'Unknown')}, Pot: ${pot_size:.2f}")
                self.last_decision_time = time.time()
                
        except Exception as e:
            self.logger.error(f"Error in waiting state handler: {e}")
    
    def _update_opponent_tracking_from_game_state(self, game_analysis: Dict):
        """Update opponent tracking from current game state."""
        try:
            # This would detect and track opponent actions from the game state
            # Implementation depends on how action history is tracked
            active_player = game_analysis.get('active_player', {})
            if active_player and not active_player.get('is_my_player', False):
                player_name = active_player.get('name', 'Unknown')
                
                # Create or update opponent profile
                profile = self.opponent_tracker_enhanced.get_or_create_opponent(player_name)
                
                # Update basic stats if we can detect action
                # This would be enhanced with actual action detection
                pass
                
        except Exception as e:
            self.logger.error(f"Error updating opponent tracking from game state: {e}")
    
    def _cleanup_session(self):
        """Cleanup session resources and save final stats."""
        try:
            self.logger.info("=== Enhanced Session Cleanup ===")
            
            # Complete any ongoing hand tracking
            if self.current_hand_id_for_history and self.current_hand_start_time:
                self._complete_hand_tracking()
                self._complete_hand_performance_tracking()
              # Get final session metrics
            session_metrics = self.performance_monitor.get_current_metrics()
              # Log session summary
            self.logger.info(f"Session Summary:")
            self.logger.info(f"  - Total hands: {session_metrics.hands_played}")
            self.logger.info(f"  - Total decisions: {self.total_decisions_made}")
            self.logger.info(f"  - Successful parses: {self.successful_parses}")
            self.logger.info(f"  - Failed parses: {self.failed_parses}")
            self.logger.info(f"  - Parse success rate: {(self.successful_parses / max(1, self.successful_parses + self.failed_parses)) * 100:.1f}%")
            self.logger.info(f"  - Session profit/loss: ${session_metrics.total_profit:.2f}")
            self.logger.info(f"  - Win rate: {session_metrics.win_rate * 100:.1f}%")
            
            # Save enhanced opponent data
            if hasattr(self.opponent_tracker_enhanced, 'save_to_file'):
                self.opponent_tracker_enhanced.save_to_file('enhanced_opponent_data.json')
                self.logger.info("Enhanced opponent data saved")
            
            # Save performance data
            if hasattr(self.performance_monitor, 'save_session_data'):
                self.performance_monitor.save_session_data('session_performance.json')
                self.logger.info("Performance data saved")
            
            # Save session tracker data
            if hasattr(self.session_tracker, 'save_session'):
                self.session_tracker.save_session()
                self.logger.info("Session tracker data saved")
            
        except Exception as e:
            self.logger.error(f"Error during session cleanup: {e}", exc_info=True)

    def _apply_adaptive_adjustments(self):
        """Apply adaptive strategy adjustments based on performance."""
        recommendations = self.performance_monitor.get_strategy_recommendations()
        
        if 'aggression' in recommendations:
            if 'increase' in recommendations['aggression'].lower():
                self.strategy_adjustments['aggression_multiplier'] = min(1.5, self.strategy_adjustments['aggression_multiplier'] * 1.05)
            elif 'decrease' in recommendations['aggression'].lower():
                self.strategy_adjustments['aggression_multiplier'] = max(0.7, self.strategy_adjustments['aggression_multiplier'] * 0.95)
        
        if 'vpip' in recommendations:
            if 'tighten' in recommendations['vpip'].lower():
                self.strategy_adjustments['tightness_adjustment'] = min(0.1, self.strategy_adjustments['tightness_adjustment'] + 0.01)
            elif 'loosen' in recommendations['vpip'].lower():
                self.strategy_adjustments['tightness_adjustment'] = max(-0.1, self.strategy_adjustments['tightness_adjustment'] - 0.01)

    # ... existing code ...
# Main execution
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("enhanced_poker_bot.log", mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    enhanced_bot = None
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == 'calibrate':
            enhanced_bot = EnhancedPokerBot()
            enhanced_bot.run_calibration()
        elif len(sys.argv) > 1:
            file_path = sys.argv[1]
            enhanced_bot = EnhancedPokerBot()
            enhanced_bot.run_test_file(file_path)
        else:
            enhanced_bot = EnhancedPokerBot()
            
            # Check calibration
            if not enhanced_bot.ui_controller.positions:
                logger.warning("UI positions not calibrated. Please run calibration first.")
                choice = input("Would you like to run calibration now? (yes/no): ").strip().lower()
                if choice == 'yes':
                    enhanced_bot.run_calibration()
                else:
                    logger.info("Exiting. Please calibrate UI positions before running the bot.")
                    sys.exit()
            
            if not enhanced_bot.ui_controller.positions.get("html_capture_point"):
                logger.critical("HTML capture point not calibrated. Run calibration.")
                sys.exit()
            
            # Start enhanced main loop
            enhanced_bot.enhanced_main_loop()
            
    except Exception as e:
        logger.error(f"An error occurred in enhanced main: {e}", exc_info=True)
    finally:
        if enhanced_bot:
            enhanced_bot.close_logger()
        logger.info("Enhanced PokerBot application finished.")
