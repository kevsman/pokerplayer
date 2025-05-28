"""
Game Logger for Poker Bot
Provides comprehensive logging functionality for analyzing game decisions and performance.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import csv

class GameLogger:
    """Centralized logging system for poker bot game analysis."""
    
    def __init__(self, base_log_dir: str = "logs"):
        """Initialize the game logger with separate log files for different data types."""
        self.base_log_dir = base_log_dir
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create logs directory if it doesn't exist
        os.makedirs(base_log_dir, exist_ok=True)
        
        # Initialize different loggers for different purposes
        self._setup_loggers()
        
        # Game state tracking
        self.hand_count = 0
        self.session_start_time = datetime.now()
        self.decisions_made = 0
        
        # Create CSV files for structured data
        self._setup_csv_files()
        
        self.log_session_start()
    
    def _setup_loggers(self):
        """Set up different loggers for various types of data."""
        
        # Main game log - all decisions and actions
        self.main_logger = self._create_logger(
            'main_game',
            f"{self.base_log_dir}/game_session_{self.session_id}.log",
            logging.INFO
        )
        
        # Decision analysis log - detailed decision reasoning
        self.decision_logger = self._create_logger(
            'decisions',
            f"{self.base_log_dir}/decisions_{self.session_id}.log",
            logging.DEBUG
        )
        
        # Hand history log - complete hand data
        self.hand_logger = self._create_logger(
            'hands',
            f"{self.base_log_dir}/hands_{self.session_id}.log",
            logging.INFO
        )
        
        # Error log - errors and warnings
        self.error_logger = self._create_logger(
            'errors',
            f"{self.base_log_dir}/errors_{self.session_id}.log",
            logging.WARNING
        )
        
        # Performance log - timing and performance metrics
        self.performance_logger = self._create_logger(
            'performance',
            f"{self.base_log_dir}/performance_{self.session_id}.log",
            logging.INFO
        )
    
    def _create_logger(self, name: str, filename: str, level: int) -> logging.Logger:
        """Create a logger with file handler."""
        logger = logging.getLogger(f"{name}_{self.session_id}")
        logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create file handler
        handler = logging.FileHandler(filename, mode='a', encoding='utf-8')
        handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False  # Prevent messages from being propagated to the root logger
        
        return logger
    
    def _setup_csv_files(self):
        """Set up CSV files for structured data analysis."""
        
        # Decisions CSV
        self.decisions_csv_path = f"{self.base_log_dir}/decisions_{self.session_id}.csv"
        with open(self.decisions_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'hand_id', 'game_stage', 'hand_rank', 'hand_description',
                'hole_cards', 'community_cards', 'pot_size', 'stack_size', 'bet_to_call',
                'pot_odds', 'win_probability', 'action_taken', 'amount', 'reasoning',
                'ev_fold', 'ev_check', 'ev_call', 'ev_raise', 'opponent_count'
            ])
        
        # Hand results CSV
        self.hands_csv_path = f"{self.base_log_dir}/hand_results_{self.session_id}.csv"
        with open(self.hands_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'hand_id', 'starting_stack', 'ending_stack', 'profit_loss',
                'final_hand_rank', 'actions_taken', 'total_invested', 'hand_duration'
            ])
        
        # Performance metrics CSV
        self.performance_csv_path = f"{self.base_log_dir}/performance_{self.session_id}.csv"
        with open(self.performance_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'metric_type', 'value', 'description'
            ])
    
    def log_session_start(self):
        """Log the start of a new session."""
        self.main_logger.info("="*80)
        self.main_logger.info(f"POKER BOT SESSION STARTED - ID: {self.session_id}")
        self.main_logger.info(f"Session Start Time: {self.session_start_time}")
        self.main_logger.info("="*80)
    
    def log_session_end(self):
        """Log the end of a session with summary statistics."""
        session_duration = datetime.now() - self.session_start_time
        
        self.main_logger.info("="*80)
        self.main_logger.info("POKER BOT SESSION ENDED")
        self.main_logger.info(f"Session Duration: {session_duration}")
        self.main_logger.info(f"Total Hands Played: {self.hand_count}")
        self.main_logger.info(f"Total Decisions Made: {self.decisions_made}")
        if self.hand_count > 0:
            self.main_logger.info(f"Average Decisions per Hand: {self.decisions_made / self.hand_count:.2f}")
        self.main_logger.info("="*80)
        
        # Log performance metrics
        self._log_performance_metric("session_duration_seconds", session_duration.total_seconds())
        self._log_performance_metric("total_hands", self.hand_count)
        self._log_performance_metric("total_decisions", self.decisions_made)
    
    def log_new_hand(self, hand_id: str, starting_stack: float):
        """Log the start of a new hand."""
        self.hand_count += 1
        self.main_logger.info(f"\n--- NEW HAND #{self.hand_count} ---")
        self.main_logger.info(f"Hand ID: {hand_id}")
        self.main_logger.info(f"Starting Stack: ${starting_stack:.2f}")
        
        self.hand_logger.info(f"Hand #{self.hand_count} - ID: {hand_id} - Starting Stack: ${starting_stack:.2f}")
    
    def log_decision(self, decision_data: Dict[str, Any]):
        """Log a decision with all relevant context."""
        self.decisions_made += 1
        
        # Extract key information
        timestamp = datetime.now()
        hand_id = decision_data.get('hand_id', 'Unknown')
        game_stage = decision_data.get('game_stage', 'Unknown')
        action = decision_data.get('action', 'Unknown')
        amount = decision_data.get('amount', 0)
        reasoning = decision_data.get('reasoning', 'No reasoning provided')
        
        # Log to main logger
        self.main_logger.info(f"DECISION #{self.decisions_made}: {action}" + 
                             (f" ${amount:.2f}" if amount > 0 else ""))
        self.main_logger.info(f"  Hand: {decision_data.get('hole_cards', 'Unknown')}")
        self.main_logger.info(f"  Rank: {decision_data.get('hand_description', 'Unknown')}")
        self.main_logger.info(f"  Pot: ${decision_data.get('pot_size', 0):.2f}")
        self.main_logger.info(f"  To Call: ${decision_data.get('bet_to_call', 0):.2f}")
        self.main_logger.info(f"  Reasoning: {reasoning}")
        
        # Log detailed decision analysis
        self.decision_logger.debug(f"=== DECISION ANALYSIS #{self.decisions_made} ===")
        self.decision_logger.debug(f"Timestamp: {timestamp}")
        self.decision_logger.debug(f"Hand ID: {hand_id}")
        self.decision_logger.debug(f"Game Stage: {game_stage}")
        self.decision_logger.debug(f"Hole Cards: {decision_data.get('hole_cards', 'Unknown')}")
        self.decision_logger.debug(f"Community Cards: {decision_data.get('community_cards', [])}")
        self.decision_logger.debug(f"Hand Rank: {decision_data.get('hand_rank', 'Unknown')}")
        self.decision_logger.debug(f"Hand Description: {decision_data.get('hand_description', 'Unknown')}")
        self.decision_logger.debug(f"Pot Size: ${decision_data.get('pot_size', 0):.2f}")
        self.decision_logger.debug(f"Stack Size: ${decision_data.get('stack_size', 0):.2f}")
        self.decision_logger.debug(f"Bet to Call: ${decision_data.get('bet_to_call', 0):.2f}")
        self.decision_logger.debug(f"Pot Odds: {decision_data.get('pot_odds', 0):.3f}")
        self.decision_logger.debug(f"Win Probability: {decision_data.get('win_probability', 0):.3f}")
        self.decision_logger.debug(f"Opponent Count: {decision_data.get('opponent_count', 0)}")
        
        # Log EV calculations if available
        if 'ev_calculations' in decision_data:
            ev = decision_data['ev_calculations']
            self.decision_logger.debug(f"EV Fold: {ev.get('ev_fold', 0):.2f}")
            self.decision_logger.debug(f"EV Check: {ev.get('ev_check', 0):.2f}")
            self.decision_logger.debug(f"EV Call: {ev.get('ev_call', 0):.2f}")
            self.decision_logger.debug(f"EV Raise: {ev.get('ev_raise', 0):.2f}")
        
        self.decision_logger.debug(f"ACTION TAKEN: {action}" + (f" ${amount:.2f}" if amount > 0 else ""))
        self.decision_logger.debug(f"Reasoning: {reasoning}")
        self.decision_logger.debug("="*50)
        
        # Write to CSV for structured analysis
        self._write_decision_to_csv(timestamp, decision_data)
    
    def log_game_state(self, table_data: Dict, player_data: List[Dict], my_player: Dict):
        """Log the current game state."""
        self.main_logger.info(f"\n--- GAME STATE ---")
        self.main_logger.info(f"Game Stage: {table_data.get('game_stage', 'Unknown')}")
        self.main_logger.info(f"Pot Size: ${table_data.get('pot_size', 'Unknown')}")
        self.main_logger.info(f"Community Cards: {table_data.get('community_cards', [])}")
        self.main_logger.info(f"Active Players: {len([p for p in player_data if not p.get('is_empty', True)])}")
        
        if my_player:
            self.main_logger.info(f"My Position: Seat {my_player.get('seat', 'Unknown')}")
            self.main_logger.info(f"My Stack: ${my_player.get('stack', 'Unknown')}")
            self.main_logger.info(f"My Cards: {my_player.get('cards', 'Unknown')}")
            if my_player.get('hand_evaluation'):
                hand_desc = my_player['hand_evaluation'][1] if len(my_player['hand_evaluation']) > 1 else 'Unknown'
                self.main_logger.info(f"My Hand: {hand_desc}")
    
    def log_error(self, error_msg: str, error_type: str = "ERROR", exception: Exception = None):
        """Log an error or warning."""
        self.error_logger.error(f"[{error_type}] {error_msg}")
        if exception:
            self.error_logger.error(f"Exception Details: {str(exception)}")
        
        # Also log to main logger for visibility
        self.main_logger.warning(f"[{error_type}] {error_msg}")
    
    def log_performance(self, operation: str, duration: float, details: str = ""):
        """Log performance metrics."""
        self.performance_logger.info(f"{operation}: {duration:.3f}s" + 
                                    (f" - {details}" if details else ""))
        self._log_performance_metric(operation, duration, details)
    
    def log_html_retrieval(self, success: bool, html_length: int = 0, duration: float = 0):
        """Log HTML retrieval attempts."""
        if success:
            self.main_logger.info(f"HTML Retrieved Successfully - Length: {html_length} chars in {duration:.3f}s")
        else:
            self.main_logger.warning("Failed to retrieve HTML from screen")
            self.error_logger.warning("HTML retrieval failed")
    
    def log_ui_action(self, action: str, amount: float = None, success: bool = True):
        """Log UI actions taken."""
        action_msg = f"UI Action: {action}"
        if amount is not None:
            action_msg += f" ${amount:.2f}"
        if not success:
            action_msg += " [FAILED]"
            
        self.main_logger.info(action_msg)
        
        if not success:
            self.error_logger.warning(f"UI Action Failed: {action}")
    
    def _write_decision_to_csv(self, timestamp: datetime, decision_data: Dict):
        """Write decision data to CSV file."""
        try:
            with open(self.decisions_csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                ev = decision_data.get('ev_calculations', {})
                
                writer.writerow([
                    timestamp.isoformat(),
                    decision_data.get('hand_id', ''),
                    decision_data.get('game_stage', ''),
                    decision_data.get('hand_rank', ''),
                    decision_data.get('hand_description', ''),
                    str(decision_data.get('hole_cards', [])),
                    str(decision_data.get('community_cards', [])),
                    decision_data.get('pot_size', 0),
                    decision_data.get('stack_size', 0),
                    decision_data.get('bet_to_call', 0),
                    decision_data.get('pot_odds', 0),
                    decision_data.get('win_probability', 0),
                    decision_data.get('action', ''),
                    decision_data.get('amount', 0),
                    decision_data.get('reasoning', ''),
                    ev.get('ev_fold', 0),
                    ev.get('ev_check', 0),
                    ev.get('ev_call', 0),
                    ev.get('ev_raise', 0),
                    decision_data.get('opponent_count', 0)
                ])
        except Exception as e:
            self.error_logger.error(f"Failed to write decision to CSV: {e}")
    
    def _log_performance_metric(self, metric_type: str, value: float, description: str = ""):
        """Log a performance metric to CSV."""
        try:
            with open(self.performance_csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    metric_type,
                    value,
                    description
                ])
        except Exception as e:
            self.error_logger.error(f"Failed to write performance metric to CSV: {e}")
    
    def create_summary_report(self) -> str:
        """Create a summary report of the session."""
        try:
            summary = []
            summary.append("="*60)
            summary.append(f"POKER BOT SESSION SUMMARY - {self.session_id}")
            summary.append("="*60)
            summary.append(f"Session Duration: {datetime.now() - self.session_start_time}")
            summary.append(f"Total Hands Played: {self.hand_count}")
            summary.append(f"Total Decisions Made: {self.decisions_made}")
            summary.append("")
            summary.append("Log Files Generated:")
            summary.append(f"  - Main Game Log: game_session_{self.session_id}.log")
            summary.append(f"  - Decision Analysis: decisions_{self.session_id}.log")
            summary.append(f"  - Hand History: hands_{self.session_id}.log")
            summary.append(f"  - Error Log: errors_{self.session_id}.log")
            summary.append(f"  - Performance Log: performance_{self.session_id}.log")
            summary.append("")
            summary.append("CSV Data Files:")
            summary.append(f"  - Decisions: decisions_{self.session_id}.csv")
            summary.append(f"  - Hand Results: hand_results_{self.session_id}.csv")
            summary.append(f"  - Performance: performance_{self.session_id}.csv")
            summary.append("="*60)
            
            report = "\n".join(summary)
            
            # Save summary to file
            summary_path = f"{self.base_log_dir}/session_summary_{self.session_id}.txt"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            return report
            
        except Exception as e:
            self.error_logger.error(f"Failed to create summary report: {e}")
            return f"Failed to create summary report: {e}"

# Global logger instance - will be initialized when first imported
_game_logger = None

def get_logger() -> GameLogger:
    """Get the global game logger instance."""
    global _game_logger
    if _game_logger is None:
        _game_logger = GameLogger()
    return _game_logger

def initialize_logger(base_log_dir: str = "logs") -> GameLogger:
    """Initialize the global game logger with custom directory."""
    global _game_logger
    _game_logger = GameLogger(base_log_dir)
    return _game_logger
