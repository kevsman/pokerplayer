# enhanced_poker_bot.py
"""
Enhanced poker bot with all improvements integrated:
1. Fixed opponent data collection
2. Improved action detection
3. Better timing control
4. Session performance tracking
5. Adaptive strategy adjustments
"""

import logging
import time
import sys
from typing import Dict, List, Optional, Tuple, Any

# Import all our enhanced modules
from enhanced_opponent_analysis import get_enhanced_opponent_analysis
from improved_postflop_decisions import make_improved_postflop_decision, format_decision_explanation
from enhanced_ui_detection import EnhancedUIDetection, create_smart_timing_controller
from session_performance_tracker import SessionPerformanceTracker, HandResult, get_session_tracker

# Import existing modules
from poker_bot import PokerBot
from decision_engine import ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE

class EnhancedPokerBot(PokerBot):
    """Enhanced poker bot with all improvements integrated."""
    
    def __init__(self, config_path='config.json'):
        super().__init__(config_path)
        
        # Initialize enhanced components
        self.ui_detector = EnhancedUIDetection(self.logger)
        self.timing_controller = create_smart_timing_controller()
        self.session_tracker = get_session_tracker()
        
        # Enhanced tracking
        self.current_hand_start_time = None
        self.current_hand_starting_stack = 0.0
        self.current_hand_actions = []
        self.last_decision_time = 0.0
        self.consecutive_parse_failures = 0
        
        # Performance metrics
        self.total_decisions_made = 0
        self.successful_parses = 0
        self.failed_parses = 0
        
        self.logger.info("Enhanced Poker Bot initialized with all improvements")
    
    def enhanced_main_loop(self):
        """Enhanced main loop with improved timing, detection, and tracking."""
        
        self.logger.info("Enhanced Poker Bot - Main Loop Started")
        self.session_tracker.start_new_session(100.0)  # Assuming $100 starting stack
        
        try:
            while True:
                # Smart timing decision
                if not self.ui_detector.should_parse_now():
                    time.sleep(0.2)  # Short sleep when not needed
                    continue
                
                self.logger.info("\n--- Enhanced Decision Cycle ---")
                current_time = time.time()
                
                # Get HTML with enhanced error handling
                current_html = self._get_html_with_enhanced_retry()
                if not current_html:
                    self.consecutive_parse_failures += 1
                    if self.consecutive_parse_failures > 10:
                        self.logger.error("Too many consecutive parse failures. Taking extended break.")
                        time.sleep(5.0)
                        self.consecutive_parse_failures = 0
                    continue
                
                # Parse HTML with enhanced detection
                parsed_result = self._enhanced_parse_html(current_html)
                if not parsed_result:
                    continue
                
                # Track successful parse
                self.successful_parses += 1
                self.consecutive_parse_failures = 0
                
                # Enhanced game state analysis
                game_analysis = self._enhanced_game_analysis(parsed_result)
                if not game_analysis:
                    continue
                
                # Decision making with enhanced logic
                if game_analysis['my_turn']:
                    decision_result = self._make_enhanced_decision(game_analysis)
                    if decision_result:
                        self._execute_enhanced_action(decision_result, game_analysis)
                else:
                    self._handle_waiting_state(game_analysis)
                
                # Adaptive timing
                activity_level = self._assess_game_activity(game_analysis)
                sleep_time = self.timing_controller.get_next_delay(activity_level)
                time.sleep(sleep_time)
                
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
    
    def _enhanced_parse_html(self, html_content: str) -> Optional[Dict]:
        """Parse HTML with enhanced detection and validation."""
        
        try:
            # Use enhanced UI detection
            action_results = self.ui_detector.enhanced_action_detection(
                self.parser.soup if hasattr(self.parser, 'soup') else None
            )
            
            # Standard parsing
            parsed_state = self.parser.parse_html(html_content)
            if not parsed_state or parsed_state.get('error'):
                self.logger.warning(f"Standard parsing failed: {parsed_state.get('error') if parsed_state else 'None returned'}")
                return None
            
            # Analyze table and players
            self.analyze()
            
            # Combine results
            enhanced_result = {
                'parsed_state': parsed_state,
                'action_detection': action_results,
                'table_data': self.table_data,
                'player_data': self.player_data,
                'my_player': self.get_my_player(),
                'active_player': self.get_active_player(),
                'game_state_changed': action_results.get('game_state_changed', False),
                'actions_available': action_results.get('actions_found', [])
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
                parsed_result['action_detection'].get('my_turn', False) or
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
        """Make decision using enhanced postflop logic."""
        
        try:
            my_player = game_analysis['my_player']
            table_data = game_analysis['table_data']
            opponent_analysis = game_analysis['opponent_analysis']
            
            # Get decision context
            win_probability = my_player.get('win_probability', 0.0)
            bet_to_call = my_player.get('bet_to_call', 0.0)
            can_check = 'check' in [action.get('type', '').lower() for action in game_analysis['actions_available']]
            pot_size = game_analysis['pot_size']
            stack = self._parse_stack_amount(my_player.get('stack', '0'))
            
            # Calculate pot odds
            pot_odds = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 0
            
            # Get aggression factor from session performance
            session_stats = self.session_tracker.get_session_statistics()
            base_aggression = session_stats.get('aggression_factor', 1.0)
              # Use improved postflop decision logic
            decision_result = make_improved_postflop_decision(
                game_analysis=game_analysis,
                equity_calculator=self.equity_calculator,
                opponent_analysis=opponent_analysis,
                logger_instance=self.logger,
                street=game_analysis['game_stage'].lower(),
                my_player_data=my_player,
                pot_size=pot_size,
                win_probability=win_probability,
                pot_odds=pot_odds,
                bet_to_call=bet_to_call,
                can_check=can_check,
                max_bet_on_table=self._get_max_bet_on_table(game_analysis),
                active_opponents_count=game_analysis['active_opponents_count'],
                action_history=self.action_history,
                opponent_tracker=self.opponent_tracker,
                aggression_factor=base_aggression,
                position=my_player.get('position', 'Unknown')
            )
            
            # Extract action and amount from result
            action = decision_result.get('action', 'fold')
            amount = decision_result.get('amount', 0.0)
            
            # Record decision
            decision_context = {
                'hand_id': game_analysis['hand_id'],
                'street': game_analysis['game_stage'],
                'position': my_player.get('position'),
                'win_probability': win_probability,
                'pot_odds': pot_odds,
                'opponent_count': game_analysis['active_opponents_count'],
                'stack_size': stack
            }
            
            self.session_tracker.record_decision(action, decision_context)
            self.total_decisions_made += 1
            
            decision_result = {
                'action': action,
                'amount': amount,
                'reasoning': f"Enhanced logic: {action} based on win_prob={win_probability:.2f}, pot_odds={pot_odds:.2f}",
                'context': decision_context
            }
            
            # Log decision with enhanced explanation
            explanation = format_decision_explanation(action, amount, decision_result['reasoning'])
            self.logger.info(explanation)
            
            return decision_result
            
        except Exception as e:
            self.logger.error(f"Enhanced decision making error: {e}")
            # Fallback to conservative play
            return {'action': ACTION_FOLD, 'amount': 0, 'reasoning': 'Error fallback'}
    
    def _execute_enhanced_action(self, decision_result: Dict, game_analysis: Dict):
        """Execute action with enhanced tracking and error handling."""
        
        try:
            action = decision_result['action']
            amount = decision_result.get('amount', 0)
            
            # Record action in current hand tracking
            action_record = {
                'action_type': action.upper(),
                'amount': amount,
                'street': game_analysis['game_stage'].lower(),
                'timestamp': time.time(),
                'context': decision_result.get('context', {}),
                'is_bot': True
            }
            self.current_hand_actions.append(action_record)
            
            # Execute UI action with enhanced error handling
            success = self._execute_ui_action_safely(action, amount)
            
            if success:
                self.logger.info(f"Successfully executed: {action} {amount}")
                self.timing_controller.record_activity('action_taken')
                self.last_decision_time = time.time()
                
                # Record in action history for opponent tracking
                self.action_history.append(action_record)
                  # Take break after action
                time.sleep(self.config.get_setting('delays', {}).get('after_action_delay', 2.0))
            else:
                self.logger.warning(f"Failed to execute action: {action}")
        
        except Exception as e:
            self.logger.error(f"Error executing enhanced action: {e}")
    
    def _execute_ui_action_safely(self, action: str, amount: float) -> bool:
        """Execute UI action with safety checks and retries."""
        
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                if action == ACTION_FOLD:
                    return self.ui_controller.action_fold()
                elif action == ACTION_CHECK:
                    return self.ui_controller.action_check_call()
                elif action == ACTION_CALL:
                    return self.ui_controller.action_check_call()
                elif action == ACTION_RAISE:
                    if amount > 0:
                        return self.ui_controller.action_raise(amount)
                    else:
                        return self.ui_controller.action_raise(0)
                else:
                    self.logger.warning(f"Unknown action type: {action}")
                    return False
            
            except Exception as e:
                self.logger.warning(f"UI action attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)
        
        return False
    
    def _handle_waiting_state(self, game_analysis: Dict):
        """Handle state when it's not our turn."""
        
        active_player = game_analysis.get('active_player')
        if active_player:
            self.logger.info(f"Waiting... Active player: {active_player.get('name', 'Unknown')}")
        else:
            self.logger.info("Waiting... No active player detected")
        
        # Record activity
        self.timing_controller.record_activity('waiting')
        
        # Parse opponent actions if any new ones detected
        self._update_opponent_tracking(game_analysis)
    
    def _update_opponent_tracking(self, game_analysis: Dict):
        """Update opponent tracking with any new actions detected."""
        
        try:
            # This would need to be implemented based on action history parsing
            # For now, just log that we're tracking
            if self.opponent_tracker and len(self.action_history) > 0:
                self.logger.debug(f"Tracking opponents: {len(self.opponent_tracker.opponents)} profiles")
        
        except Exception as e:
            self.logger.debug(f"Error updating opponent tracking: {e}")
    
    def _assess_game_activity(self, game_analysis: Dict) -> str:
        """Assess current game activity level for adaptive timing."""
        
        # High activity: Our turn or recent game state change
        if (game_analysis['my_turn'] or 
            game_analysis.get('game_state_changed', False) or
            time.time() - self.last_decision_time < 5.0):
            return 'high'
        
        # Low activity: Long time since last action
        elif time.time() - self.last_decision_time > 30.0:
            return 'low'
        
        # Normal activity
        else:
            return 'normal'
    
    def _cleanup_session(self):
        """Clean up session data and save performance tracking."""
        
        try:
            # Complete current hand if in progress
            if self.current_hand_id_for_history:
                self._complete_hand_tracking()
            
            # Save session data
            self.session_tracker.save_session_data()
            
            # Generate session report
            report = self.session_tracker.generate_session_report()
            self.logger.info(f"Session Report:\n{report}")
            
            # Log final statistics
            self.logger.info(f"Total decisions made: {self.total_decisions_made}")
            self.logger.info(f"Successful parses: {self.successful_parses}")
            self.logger.info(f"Failed parses: {self.failed_parses}")
            
            if self.successful_parses > 0:
                success_rate = self.successful_parses / (self.successful_parses + self.failed_parses) * 100
                self.logger.info(f"Parse success rate: {success_rate:.1f}%")
        
        except Exception as e:
            self.logger.error(f"Error during session cleanup: {e}")
        
        # Close logger
        self.close_logger()
    
    # Helper methods
    def _parse_stack_amount(self, stack_str: str) -> float:
        """Parse stack amount from string."""
        if isinstance(stack_str, (int, float)):
            return float(stack_str)
        
        cleaned = stack_str.replace('€', '').replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _get_current_stack(self) -> float:
        """Get current stack amount."""
        my_player = self.get_my_player()
        if my_player:
            return self._parse_stack_amount(my_player.get('stack', '0'))
        return 0.0
    
    def _get_last_known_position(self) -> str:
        """Get last known position."""
        my_player = self.get_my_player()
        return my_player.get('position', 'Unknown') if my_player else 'Unknown'
    
    def _extract_win_probabilities(self) -> List[float]:
        """Extract win probabilities from current hand actions."""
        probs = []
        for action in self.current_hand_actions:
            if 'win_probability' in action.get('context', {}):
                probs.append(action['context']['win_probability'])
        return probs
    
    def _was_showdown(self) -> bool:
        """Determine if hand went to showdown."""
        # Basic heuristic: if we took actions on river, likely went to showdown
        river_actions = [a for a in self.current_hand_actions if a.get('street') == 'river']
        return len(river_actions) > 0
    
    def _get_hand_strength_summary(self) -> str:
        """Get summary of hand strength throughout the hand."""
        my_player = self.get_my_player()
        if my_player and my_player.get('hand_evaluation'):
            return my_player['hand_evaluation'][1]  # Hand description
        return 'Unknown'
    
    def _get_max_bet_on_table(self, game_analysis: Dict) -> float:
        """Get maximum bet on table."""
        max_bet = 0.0
        for player in game_analysis.get('player_data', []):
            bet_str = player.get('bet', '0')
            bet_amount = self._parse_stack_amount(bet_str)
            max_bet = max(max_bet, bet_amount)
        return max_bet

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
