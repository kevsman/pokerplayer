"""
Strategy lookup module for PokerBotV2.
Stores and retrieves precomputed strategies for abstracted game states.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

class StrategyLookup:
    def __init__(self, strategy_file='strategy_table.json'):
        self.strategy_file = strategy_file
        logger.info(f"Initializing StrategyLookup with file: {strategy_file}")
        self.strategy_table = self._load_strategy_table()
        
        # Create index for faster fuzzy matching
        self._build_lookup_index()
        
        logger.info(f"Loaded {len(self.strategy_table)} strategies from file")

    def _build_lookup_index(self):
        """Build index for faster fuzzy strategy lookup."""
        self.stage_index = {}  # stage -> list of keys
        self.hand_buckets = set()  # all unique hand buckets
        self.board_buckets = set()  # all unique board buckets
        
        logger.info("Building strategy lookup index...")
        
        for key in self.strategy_table.keys():
            try:
                if len(key) >= 3:
                    stage, hand_bucket, board_bucket = str(key[0]), str(key[1]), str(key[2])
                    
                    # Index by stage
                    if stage not in self.stage_index:
                        self.stage_index[stage] = []
                    self.stage_index[stage].append(key)
                    
                    # Collect unique buckets
                    self.hand_buckets.add(hand_bucket)
                    self.board_buckets.add(board_bucket)
            except (ValueError, TypeError, IndexError):
                continue
        
        logger.info(f"Built index: {len(self.stage_index)} stages, {len(self.hand_buckets)} hand buckets, {len(self.board_buckets)} board buckets")

    def update_and_save_strategy_table(self, nodes):
        """Updates the strategy table from CFR nodes and saves to file."""
        # Convert CFR nodes to a strategy dictionary
        new_strategies = {key: node.get_average_strategy() for key, node in nodes.items()}
        
        # Merge new strategies into the main table
        self.strategy_table.update(new_strategies)
        
        # Save the updated table
        self._save_strategy_table()

    def _load_strategy_table(self):
        if not os.path.exists(self.strategy_file):
            logger.info(f"Strategy file {self.strategy_file} does not exist, starting with empty table")
            return {}
        try:
            import ast
            with open(self.strategy_file, 'r') as f:
                # Keys are stored as strings in JSON, so we need to convert them back to tuples
                string_keys_table = json.load(f)
                result = {ast.literal_eval(k): v for k, v in string_keys_table.items()}
                logger.info(f"Successfully loaded {len(result)} strategies from {self.strategy_file}")
                return result
        except (json.JSONDecodeError, IOError, ValueError, SyntaxError) as e:
            logger.error(f"Error loading strategy file {self.strategy_file}: {e}")
            return {}

    def _save_strategy_table(self):
        logger.info(f"Saving {len(self.strategy_table)} strategies to {self.strategy_file}")
        temp_file = self.strategy_file + '.tmp'
        try:
            with open(temp_file, 'w') as f:
                # JSON keys must be strings, so we convert tuples to strings
                string_keys_table = {str(k): v for k, v in self.strategy_table.items()}
                json.dump(string_keys_table, f, indent=4)
            # Atomically move the file
            os.replace(temp_file, self.strategy_file)
            logger.info(f"Successfully saved strategies to {self.strategy_file}")
        except (IOError, TypeError, json.JSONDecodeError) as e:
            logger.error(f"Error saving strategy file {self.strategy_file}: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file) # Clean up temp file on error
            pass # Handle file write errors if necessary

    def get_strategy(self, stage, hand_bucket, board_bucket, actions):
        key = (stage, hand_bucket, board_bucket, tuple(sorted(actions)))
        
        # Try exact match first
        exact_match = self.strategy_table.get(key, None)
        if exact_match:
            logger.debug(f"✅ Exact strategy match found for {key}")
            return exact_match
        
        # If no exact match, try fuzzy matching
        fuzzy_match = self._find_fuzzy_strategy_match(stage, hand_bucket, board_bucket, actions)
        if fuzzy_match:
            logger.debug(f"🎯 Fuzzy strategy match found for {key}")
            return fuzzy_match
        
        logger.debug(f"❌ No strategy match found for {key}")
        return None
    
    def _find_fuzzy_strategy_match(self, target_stage, target_hand_bucket, target_board_bucket, target_actions):
        """Find approximate strategy matches when exact match fails - optimized version."""
        target_actions_set = set(sorted(target_actions))
        target_stage_str = str(target_stage)
        
        # Only search within the same stage for performance
        if target_stage_str not in self.stage_index:
            return None
        
        best_match = None
        best_score = 0
        
        # Convert target buckets for comparison
        try:
            target_hand_int = int(target_hand_bucket)
            # Handle board buckets - they can be strings like 'pot2.9' or integers
            if isinstance(target_board_bucket, str) and target_board_bucket.startswith('pot'):
                target_board_value = float(target_board_bucket[3:])  # Extract numeric part
            else:
                target_board_value = float(target_board_bucket)
        except (ValueError, TypeError):
            return None
        
        # Search only keys in the same stage (much faster)
        for key in self.stage_index[target_stage_str]:
            try:
                stage, hand_bucket, board_bucket = str(key[0]), str(key[1]), str(key[2])
                actions = key[3] if len(key) > 3 else ()
                
                hand_int = int(hand_bucket)
                
                # Handle board bucket comparison
                if isinstance(board_bucket, str) and board_bucket.startswith('pot'):
                    board_value = float(board_bucket[3:])  # Extract numeric part
                else:
                    board_value = float(board_bucket)
                    
            except (ValueError, TypeError, IndexError):
                continue
            
            # Calculate similarity score (0-100)
            score = 40  # Base score for same stage
            
            # Actions match (important for decision type)
            actions_set = set(actions)
            if actions_set == target_actions_set:
                score += 30  # Exact action set match
            elif len(actions_set.intersection(target_actions_set)) > 0:
                score += 15  # Some actions overlap
            
            # Hand bucket similarity (moderate importance)
            hand_diff = abs(hand_int - target_hand_int)
            if hand_diff == 0:
                score += 25  # Exact hand bucket
            elif hand_diff <= 10:
                score += 20  # Very close
            elif hand_diff <= 50:
                score += 15 - (hand_diff // 10)  # Close hand bucket
            elif hand_diff <= 200:
                score += 5  # Somewhat close
            
            # Board bucket similarity (lower importance for preflop, but more for postflop)
            board_diff = abs(board_value - target_board_value)
            if board_diff < 0.1:  # Very close pot odds
                score += 10  # Exact or very close board bucket
            elif board_diff <= 0.5:
                score += 8  # Close board bucket
            elif board_diff <= 1.0:
                score += 5  # Somewhat close
            elif board_diff <= 2.0:
                score += 2  # Distant but usable
            
            # Keep track of best match (lowered threshold for better coverage)
            if score > best_score and score >= 65:  # 65% threshold for better coverage
                best_score = score
                best_match = self.strategy_table[key]
        
        if best_match:
            logger.info(f"🎯 Fuzzy match found with score {best_score}/100")
        
        return best_match

    def add_strategy(self, stage, hand_bucket, board_bucket, actions, strategy):
        key = (stage, hand_bucket, board_bucket, tuple(sorted(actions)))
        self.strategy_table[key] = strategy
        logger.debug(f"Added strategy for key: {key}")
        # Don't save after every addition - save only when explicitly called

    def update_strategy(self, stage, hand_bucket, board_bucket, actions, strategy):
        """Update strategy - alias for add_strategy for compatibility"""
        logger.debug(f"update_strategy called: stage={stage}, hand_bucket={hand_bucket}, board_bucket={board_bucket}, actions={actions}")
        self.add_strategy(stage, hand_bucket, board_bucket, actions, strategy)

    def save_strategies(self):
        """Saves the current strategy table to the file."""
        self._save_strategy_table()

    def save_strategy(self, info_set, strategy_dict):
        """Save a single strategy from training - parses info_set format."""
        try:
            # Parse info_set format: "street|hand_bucket|board_bucket|history"
            parts = info_set.split('|', 3)
            if len(parts) >= 3:
                street, hand_bucket, board_bucket = parts[0], parts[1], parts[2]
                actions = list(strategy_dict.keys())
                self.add_strategy(street, hand_bucket, board_bucket, actions, strategy_dict)
                logger.debug(f"Saved strategy: {info_set} -> {strategy_dict}")
            else:
                logger.warning(f"Invalid info_set format: {info_set}")
        except Exception as e:
            logger.error(f"Error saving strategy {info_set}: {e}")

    def apply_poker_sanity_checks(self, strategy, hand_strength, pot_odds, street="0"):
        """Apply poker sanity checks to override clearly suboptimal strategies."""
        if not strategy:
            return strategy
        
        modified = False
        original_strategy = strategy.copy()
        
        # SANITY CHECK 1: Premium hands should almost never fold preflop
        if street == "0" and hand_strength > 0.8:  # Premium hands (AA, KK, AKs, etc.)
            if strategy.get('fold', 0) > 0.3:  # If strategy says fold >30%
                logger.info(f"🔧 SANITY CHECK: Premium hand folding {strategy.get('fold', 0):.1%} -> reducing to 5%")
                # Redistribute probabilities to favor raising
                strategy['fold'] = 0.05
                strategy['raise'] = strategy.get('raise', 0) + 0.6
                strategy['call'] = strategy.get('call', 0) + 0.1
                # Normalize
                total = sum(strategy.values())
                strategy = {k: v/total for k, v in strategy.items()}
                modified = True
        
        # SANITY CHECK 2: Very strong hands should raise more than fold
        if hand_strength > 0.75:
            if strategy.get('fold', 0) > strategy.get('raise', 0):
                logger.info(f"🔧 SANITY CHECK: Strong hand folding more than raising -> adjusting")
                # Swap fold and raise probabilities
                fold_prob = strategy.get('fold', 0)
                raise_prob = strategy.get('raise', 0)
                strategy['fold'] = min(0.2, raise_prob)  # Cap fold at 20%
                strategy['raise'] = max(0.4, fold_prob)  # Boost raise to at least 40%
                # Normalize
                total = sum(strategy.values())
                strategy = {k: v/total for k, v in strategy.items()}
                modified = True
        
        # SANITY CHECK 3: Extremely favorable pot odds should rarely fold
        if pot_odds < 0.2 and hand_strength > 0.3:  # Good pot odds with decent hand
            if strategy.get('fold', 0) > 0.6:  # Folding >60% with good odds
                logger.info(f"🔧 SANITY CHECK: Folding {strategy.get('fold', 0):.1%} with good pot odds -> adjusting")
                strategy['fold'] = 0.3  # Reduce fold to 30%
                strategy['call'] = strategy.get('call', 0) + 0.3  # Increase call
                # Normalize
                total = sum(strategy.values())
                strategy = {k: v/total for k, v in strategy.items()}
                modified = True
        
        if modified:
            logger.debug(f"Strategy adjusted: {original_strategy} -> {strategy}")
        
        return strategy
