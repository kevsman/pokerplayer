"""
Safe Strategy Lookup - A conservative approach that prioritizes Monte Carlo fallback over risky fuzzy matches.
This fixes the aggressive fuzzy matching problem by implementing strict sanity checks.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

class SafeStrategyLookup:
    def __init__(self, strategy_file='strategy_table.json'):
        self.strategy_file = strategy_file
        logger.info(f"Initializing SafeStrategyLookup with file: {strategy_file}")
        self.strategy_table = self._load_strategy_table()
        
        if self.strategy_table:
            logger.info(f"✅ Loaded {len(self.strategy_table)} strategies from file.")
        else:
            logger.warning(f"⚠️ Strategy file {self.strategy_file} is empty or could not be loaded.")

    def _load_strategy_table(self):
        """Loads the strategy table from the JSON file."""
        if not os.path.exists(self.strategy_file):
            logger.error(f"Strategy file not found: {self.strategy_file}")
            return {}
        
        try:
            with open(self.strategy_file, 'r') as f:
                string_keys_table = json.load(f)
                
                # Convert string keys to integers
                converted_table = {}
                for k, v in string_keys_table.items():
                    try:
                        hash_key = int(k)
                        if isinstance(v, dict):
                            converted_table[hash_key] = v
                    except (ValueError, TypeError):
                        continue
                
                logger.info(f"Successfully loaded {len(converted_table)} strategies")
                return converted_table
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading strategy file: {e}")
            return {}

    def get_strategy_by_hash(self, info_hash: int):
        """Direct hash lookup - most reliable method."""
        return self.strategy_table.get(info_hash)
    
    def _is_strategy_safe_for_context(self, strategy: dict, context: dict) -> bool:
        """
        Determines if a strategy is safe to use in the given context.
        This prevents aggressive strategies from being applied to weak situations.
        """
        if not strategy or not context:
            return False
        
        # Extract context information
        stage = context.get('stage', 'preflop')
        hand_strength = context.get('hand_strength', 'unknown')
        
        # Calculate total aggression level (raise + all-in probability)
        total_aggression = 0.0
        for action_key, prob in strategy.items():
            if action_key in ['action_2', 'action_3', 'action_4', 'action_5']:  # All raise actions
                total_aggression += prob
        
        # SAFETY RULES:
        
        # 1. River scenarios with weak hands should not use aggressive strategies
        if stage == 'river' and hand_strength in ['weak', 'trash', 'unknown']:
            if total_aggression > 0.3:  # More than 30% aggression
                logger.warning(f"🚨 Rejecting aggressive strategy ({total_aggression:.1%} aggression) for {hand_strength} hand on river")
                return False
        
        # 2. Extremely aggressive strategies (>90% aggression) need very strong justification
        if total_aggression > 0.9:
            if stage in ['turn', 'river'] and hand_strength not in ['nuts', 'strong']:
                logger.warning(f"🚨 Rejecting ultra-aggressive strategy ({total_aggression:.1%}) for {hand_strength} hand on {stage}")
                return False
        
        # 3. All-in strategies (action_5 > 50%) are very dangerous
        all_in_prob = strategy.get('action_5', 0.0)
        if all_in_prob > 0.5:
            if stage == 'river' and hand_strength in ['weak', 'trash', 'medium', 'unknown']:
                logger.warning(f"🚨 Rejecting all-in strategy ({all_in_prob:.1%}) for {hand_strength} hand on river")
                return False
        
        return True
    
    def _get_hand_strength_from_cards(self, hole_cards: list, community_cards: list) -> str:
        """
        Quick assessment of hand strength for safety checking.
        This is a simplified version for safety checks only.
        """
        if not hole_cards or len(hole_cards) != 2:
            return 'unknown'
        
        # Very basic hand strength assessment
        # In a real implementation, you'd use the hand evaluator here
        
        # For now, return 'unknown' to be conservative
        return 'unknown'
    
    def get_strategy_with_conservative_fallback(self, info_hash: int, state_components: dict = None, 
                                              hole_cards: list = None, community_cards: list = None):
        """
        Conservative strategy lookup that prioritizes safety over coverage.
        
        Args:
            info_hash (int): The exact hash to look for
            state_components (dict): State information for context
            hole_cards (list): Player's hole cards for safety checking
            community_cards (list): Community cards for safety checking
            
        Returns:
            tuple: (strategy_dict, match_type) where match_type is 'exact', 'safe_fuzzy', or None
        """
        # Try exact match first
        exact_strategy = self.get_strategy_by_hash(info_hash)
        if exact_strategy:
            return exact_strategy, 'exact'
        
        # Create context for safety checking
        context = {
            'stage': 'preflop',  # default
            'hand_strength': 'unknown'  # conservative default
        }
        
        if state_components:
            stage_map = {0: 'preflop', 1: 'flop', 2: 'turn', 3: 'river'}
            context['stage'] = stage_map.get(state_components.get('street', 0), 'preflop')
        
        if hole_cards and community_cards is not None:
            context['hand_strength'] = self._get_hand_strength_from_cards(hole_cards, community_cards)
        
        # CONSERVATIVE FUZZY MATCHING - Only for very similar scenarios
        similar_strategies = self._get_very_similar_strategies(info_hash, max_candidates=10)
        
        for hash_key, strategy, similarity_score in similar_strategies:
            # Very strict similarity requirement
            similarity_percentage = (similarity_score / 64) * 100
            
            # Require 85% similarity for any fuzzy match (much stricter than before)
            if similarity_score >= 54:  # 54/64 = 84.375%
                # Additional safety check
                if self._is_strategy_safe_for_context(strategy, context):
                    logger.info(f"🔒 Using SAFE fuzzy match: hash {hash_key} (similarity: {similarity_percentage:.1f}%, passed safety checks)")
                    return strategy, 'safe_fuzzy'
                else:
                    logger.warning(f"⚠️ Rejected unsafe fuzzy match: hash {hash_key} (similarity: {similarity_percentage:.1f}%, failed safety checks)")
            else:
                logger.debug(f"❌ Rejected low-similarity match: {similarity_percentage:.1f}% < 85% required")
        
        # If no safe fuzzy match found, return None to trigger Monte Carlo fallback
        logger.info(f"🎲 No safe strategy match found for hash {info_hash}. Will use Monte Carlo fallback.")
        return None, None
    
    def _get_very_similar_strategies(self, target_hash: int, max_candidates: int = 10):
        """
        Find only very similar strategies with strict bit-matching criteria.
        """
        if not self.strategy_table:
            return []
        
        candidates = []
        target_bits = bin(target_hash)[2:].zfill(64)
        
        # Smaller sample size since we're being very strict
        sample_size = min(5000, len(self.strategy_table))
        strategy_items = list(self.strategy_table.items())
        step = max(1, len(strategy_items) // sample_size)
        
        for i in range(0, len(strategy_items), step):
            hash_key, strategy = strategy_items[i]
            candidate_bits = bin(hash_key)[2:].zfill(64)
            similarity = sum(1 for a, b in zip(target_bits, candidate_bits) if a == b)
            
            # Only consider very similar strategies (≥84% similarity)
            if similarity >= 54:
                candidates.append((hash_key, strategy, similarity))
        
        # Sort by similarity and return top candidates
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[:max_candidates]
