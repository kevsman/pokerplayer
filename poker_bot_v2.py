"""
poker_bot_v2.py
A next-generation PokerBot using abstraction, CFR-based solver, and strategy lookup.
"""
import sys
import time
import logging
import threading

from hand_abstraction import HandAbstraction
from cfr_solver import CFRSolver
from strategy_lookup import StrategyLookup
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator
from html_parser import PokerPageParser
from ui_controller import UIController
from decision_engine import ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE

def parse_currency_string(value_str):
    if isinstance(value_str, (int, float)):
        return float(value_str)
    if not isinstance(value_str, str):
        return 0.0
    cleaned_str = value_str.replace('€', '').replace('$', '').replace(',', '').strip()
    try:
        return float(cleaned_str)
    except ValueError:
        return 0.0

class PokerBotV2:
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.fh = None
        self.ch = None
        
        log_file_path = 'poker_bot_v2.log'
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        self.fh = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        self.fh.setLevel(logging.DEBUG)
        self.ch = logging.StreamHandler(sys.stdout)
        self.ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.fh.setFormatter(formatter)
        self.ch.setFormatter(formatter)
        
        self.logger.addHandler(self.fh)
        self.logger.addHandler(self.ch)
        self.logger.propagate = False

        self.config = config if config is not None else {}
        self.big_blind = self.config.get('big_blind', 0.04)
        self.small_blind = self.config.get('small_blind', 0.02)

        self.parser = PokerPageParser()
        self.ui_controller = UIController()
        self.hand_evaluator = HandEvaluator()
        self.equity_calculator = EquityCalculator()
        self.abstraction = HandAbstraction(self.hand_evaluator, self.equity_calculator)
        self.strategy_lookup = StrategyLookup()
        self.cfr_solver = CFRSolver(self.abstraction, self.hand_evaluator, self.equity_calculator)

        self.table_data = {}
        self.player_data = []
        self.running = False
        self.last_html_content = None
        self.starting_stack = 6

    def close_logger(self):
        if hasattr(self, 'logger') and self.logger and self.logger.hasHandlers():
            self.logger.info("Closing logger handlers.")
            if self.fh:
                self.fh.close()
                self.logger.removeHandler(self.fh)
                self.fh = None
            if self.ch:
                self.ch.close()
                self.logger.removeHandler(self.ch)
                self.ch = None
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

    def __del__(self):
        self.close_logger()

    def analyze_table(self):
        self.table_data = self.parser.analyze_table()

    def analyze_players(self):
        self.player_data = self.parser.analyze_players()

    def get_active_player(self):
        for player in self.player_data:
            if player.get('has_turn', False):
                return player
        return None
        
    def get_my_player(self):
        for player in self.player_data:
            if player.get('is_my_player', False):
                return player
        return None

    def analyze(self):
        self.analyze_table() 
        self.analyze_players() 
        return {
            'table': self.table_data,
            'players': self.player_data,
            'my_player': self.get_my_player(),
            'active_player': self.get_active_player()
        }

    def decide_action(self):
        my_player = self.get_my_player()
        if not my_player or not my_player.get('has_turn'):
            return None, None

        player_hole_cards = my_player.get('cards', [])
        if not player_hole_cards:
            self.logger.warning("Cannot decide action without hole cards.")
            return ACTION_FOLD, 0

        community_cards = self.table_data.get('community_cards', [])
        pot_size = parse_currency_string(self.table_data.get('pot_size', '0'))
        stage = self.table_data.get('game_stage', 'preflop').lower()
        actions = my_player.get('available_actions', [ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE])

        # 1. Abstract the hand and board
        hand_bucket = self.abstraction.bucket_hand(player_hole_cards, community_cards, stage)
        board_bucket = self.abstraction.bucket_board(community_cards, stage)
        
        # 2. Try to get a precomputed strategy
        strategy = self.strategy_lookup.get_strategy(stage, hand_bucket, board_bucket, actions)
        if strategy:
            self.logger.info(f"Using precomputed strategy for {stage}, hand bucket {hand_bucket}, board bucket {board_bucket}")
        else:
            # 3. If not found, run a quick CFR solve for this spot
            self.logger.info("No precomputed strategy found. Running real-time CFR solve.")
            strategy = self.cfr_solver.solve(player_hole_cards, community_cards, pot_size, actions, stage)

        # 4. Pick the action with the highest probability
        best_action = max(strategy.items(), key=lambda x: x[1])[0]
        self.logger.info(f"Bot decision: {best_action} (strategy: {strategy})")

        # 5. Determine amount
        amount = 0
        if best_action == ACTION_RAISE:
            # Placeholder for raise sizing. A real implementation would have smarter sizing.
            amount = pot_size * 0.75 
        elif best_action == ACTION_CALL:
            amount = parse_currency_string(my_player.get('bet_to_call', '0'))

        return best_action, amount

    def start_kill_switch_listener(self):
        try:
            import keyboard
        except ImportError:
            self.logger.warning("'keyboard' library not found. Kill switch disabled.")
            return
        def listen():
            keyboard.wait('ctrl+q')
            self.logger.info("Ctrl+Q detected. Stopping bot.")
            self.running = False
        t = threading.Thread(target=listen, daemon=True)
        t.start()

    def main_loop(self):
        self.running = True
        self.start_kill_switch_listener()
        self.logger.info("PokerBotV2 started. Press Ctrl+Q to stop.")
        
        if not self.ui_controller.positions:
            self.logger.warning("UI positions not calibrated. Please run calibration first.")
            return

        try:
            while self.running:
                self.logger.info("\n--- New Decision Cycle ---")
                current_html = self.ui_controller.get_html_from_screen_with_auto_retry()

                if not current_html:
                    self.logger.warning("Failed to retrieve HTML. Retrying...")
                    time.sleep(1)
                    continue
                
                self.last_html_content = current_html
                parsed_state = self.parser.parse_html(current_html)
                
                if not parsed_state or parsed_state.get('error'):
                    self.logger.error(f"Failed to parse HTML: {parsed_state.get('error', 'Unknown') if parsed_state else 'None'}. Retrying...")
                    time.sleep(1)
                    continue

                self.analyze()
                my_player = self.get_my_player()

                if my_player and my_player.get('has_turn'):
                    self.logger.info("My turn to act.")
                    action, amount = self.decide_action()

                    if action:
                        self.logger.info(f"Decision: {action}, Amount: {amount}")
                        if action == ACTION_FOLD:
                            self.ui_controller.action_fold()
                        elif action == ACTION_CHECK or action == ACTION_CALL:
                            self.ui_controller.action_check_call()
                        elif action == ACTION_RAISE:
                            self.ui_controller.action_raise(amount)
                        time.sleep(self.config.get('delays', {}).get('after_action_delay', 5.0))
                    else:
                        self.logger.warning("Could not determine an action. Waiting.")
                else:
                    self.logger.info("Not my turn. Waiting...")
                
                time.sleep(self.config.get('delays', {}).get('main_loop_general_delay', 0.25))

        except KeyboardInterrupt:
            self.logger.info("PokerBot stopped by user.")
        finally:
            self.running = False
            self.logger.info("PokerBot main_loop ended.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    bot = None
    try:
        bot = PokerBotV2()
        if not bot.ui_controller.positions:
            logger.critical("UI positions not calibrated. Run the original poker_bot.py with 'calibrate' argument first.")
            sys.exit()
        bot.main_loop()
    except Exception as e:
        logger.error(f"An error occurred in __main__: {e}", exc_info=True)
    finally:
        if bot:
            bot.close_logger()
        logger.info("PokerBotV2 application finished.")
