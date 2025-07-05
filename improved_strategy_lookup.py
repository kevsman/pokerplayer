"""
Enhanced Strategy lookup module for PokerBotV2.
Loads and retrieves pre-computed strategies from a strategy file using a direct hash lookup
with improved fuzzy matching for better strategy coverage.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

class StrategyLookup:
    def __init__(self, strategy_file='strategy_table.json'):
        self.strategy_file = strategy_file
        logger.info(f"Initializing Enhanced StrategyLookup with file: {strategy_file}")
        self.strategy_table = self._load_strategy_table()
        
        if self.strategy_table:
            logger.info(f"✅ Loaded {len(self.strategy_table)} strategies from file.")
        else:
            logger.warning(f"⚠️ Strategy file {self.strategy_file} is empty or could not be loaded.")

    def _load_strategy_table(self):
        """Loads the strategy table from the JSON file with corruption recovery."""
        if not os.path.exists(self.strategy_file):
            logger.error(f"Strategy file not found: {self.strategy_file}")
            return {}
        
        # Try to load main file
        for attempt_file in [self.strategy_file, self.strategy_file + ".backup"]:
            if not os.path.exists(attempt_file):
                continue
                
            try:
                logger.info(f"Attempting to load strategies from: {attempt_file}")
                with open(attempt_file, 'r') as f:
                    # Keys are stored as strings in JSON, so we convert them back to integers for lookup.
                    string_keys_table = json.load(f)
                    
                    # Validate the data structure
                    if not isinstance(string_keys_table, dict):
                        raise ValueError("Strategy file does not contain a valid dictionary")
                    
                    # Use a dictionary comprehension for efficient conversion with error handling
                    converted_table = {}
                    invalid_entries = 0
                    
                    for k, v in string_keys_table.items():
                        try:
                            hash_key = int(k)
                            if isinstance(v, dict) and all(isinstance(val, (int, float)) for val in v.values()):
                                converted_table[hash_key] = v
                            else:
                                invalid_entries += 1
                        except (ValueError, TypeError):
                            invalid_entries += 1
                    
                    if invalid_entries > 0:
                        logger.warning(f"Skipped {invalid_entries} invalid strategy entries")
                    
                    logger.info(f"Successfully loaded {len(converted_table)} valid strategies from {attempt_file}")
                    return converted_table
                    
            except (json.JSONDecodeError, IOError, ValueError) as e:
                logger.error(f"Error loading strategy file {attempt_file}: {e}")
                if attempt_file == self.strategy_file:
                    logger.info("Trying backup file...")
                    continue
        
        logger.error("All strategy file loading attempts failed")
        return {}

    def get_strategy_by_hash(self, info_hash: int):
        """
        Retrieves a strategy directly using the information state hash.
        
        Args:
            info_hash (int): The hash representing the current game state.
            
        Returns:
            dict: The strategy dictionary if found, otherwise None.
        """
        return self.strategy_table.get(info_hash)
    
    def get_similar_strategies(self, target_hash: int, max_candidates: int = 100):
        """
        Find strategies with similar hash values for fuzzy matching.
        Increased candidate pool for better coverage.
        
        Args:
            target_hash (int): The target hash we're looking for
            max_candidates (int): Maximum number of candidates to return
            
        Returns:
            list: List of (hash, strategy, similarity_score) tuples, sorted by similarity
        """
        if not self.strategy_table:
            return []
        
        candidates = []
        target_bits = bin(target_hash)[2:].zfill(64)  # Convert to 64-bit binary string
        
        # Increased sample size for better coverage
        sample_size = min(20000, len(self.strategy_table))  # Doubled from 10k
        strategy_items = list(self.strategy_table.items())
        step = max(1, len(strategy_items) // sample_size)
        
        for i in range(0, len(strategy_items), step):
            hash_key, strategy = strategy_items[i]
            
            # Calculate bit similarity (Hamming distance)
            candidate_bits = bin(hash_key)[2:].zfill(64)
            similarity = sum(1 for a, b in zip(target_bits, candidate_bits) if a == b)
            
            candidates.append((hash_key, strategy, similarity))
            
            if len(candidates) >= max_candidates * 2:  # Get extra for better sorting
                break
        
        # Sort by similarity (higher is better) and return top candidates
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[:max_candidates]
    
    def get_strategy_with_fuzzy_fallback(self, info_hash: int, state_components: dict = None):
        """
        Get strategy with improved fuzzy matching fallback when exact match fails.
        
        Args:
            info_hash (int): The exact hash to look for first
            state_components (dict): Components used to build the hash for component-wise matching
            
        Returns:
            tuple: (strategy_dict, match_type) where match_type is 'exact', 'fuzzy', or None
        """
        # Try exact match first
        exact_strategy = self.get_strategy_by_hash(info_hash)
        if exact_strategy:
            return exact_strategy, 'exact'
        
        # Try fuzzy matching with similar hashes - more lenient threshold
        similar_strategies = self.get_similar_strategies(info_hash, max_candidates=50)
        
        if similar_strategies:
            # Use the most similar strategy if it's reasonably similar
            best_hash, best_strategy, similarity_score = similar_strategies[0]
            
            # IMPROVED: Adaptive threshold based on scenario context
            similarity_percentage = (similarity_score / 64) * 100
            
            # Higher threshold for river scenarios (need 75% similarity)
            min_similarity = 48 if state_components and state_components.get('street') == 3 else 42  # 75% for river, 65% for others
            
            if similarity_score >= min_similarity:
                # Additional sanity check: reject extremely aggressive strategies on river with low similarity
                if (state_components and state_components.get('street') == 3 and 
                    similarity_score < 48 and self._is_extremely_aggressive_strategy(best_strategy)):
                    logger.warning(f"🚨 Rejecting aggressive fuzzy match on river: similarity {similarity_percentage:.1f}% too low for aggressive strategy")
                    return None, None
                
                logger.info(f"🔄 Using fuzzy match: hash {best_hash} (similarity: {similarity_score}/64 bits = {similarity_percentage:.1f}%)")
                return best_strategy, 'fuzzy'
            else:
                required_pct = 75 if state_components and state_components.get('street') == 3 else 65
                logger.info(f"❌ Rejecting fuzzy match: similarity {similarity_score}/64 bits = {similarity_percentage:.1f}% too low (need ≥{required_pct}%)")
        
        # Try component-wise fuzzy matching if we have state components
        if state_components:
            component_strategy = self._get_strategy_by_components(state_components)
            if component_strategy:
                return component_strategy, 'component'
        
        return None, None
    
    def _get_strategy_by_components(self, state_components: dict):
        """
        Find strategies with similar state components with BALANCED matching for good coverage.
        
        Args:
            state_components (dict): Dictionary with 'street', 'turn_index', 'pot_range', etc.
            
        Returns:
            dict: Strategy dictionary if found, otherwise None
        """
        if not self.strategy_table or not state_components:
            return None
        
        target_street = state_components.get('street', 0)
        target_position = state_components.get('turn_index', 0)
        target_pot = state_components.get('effective_pot', 0)
        target_players = state_components.get('num_active', 6)
        
        # BALANCED COMPONENT MATCHING: Good coverage while maintaining quality
        candidates = []
        
        # For preflop heads-up (most common case), be moderately strict
        is_preflop_heads_up = (target_street == 0 and target_players == 2)
        
        # Increased sample for better matches
        sample_items = list(self.strategy_table.items())[:25000]  # Increased from 10k
        
        for hash_key, strategy in sample_items:
            try:
                # Reverse engineer components from hash
                estimated_street = (hash_key // 10000000000) % 10
                estimated_position = (hash_key // 1000000000) % 10
                estimated_players = ((hash_key // 1000000) % 1000) // 100
                
                # BALANCED SCORING: Allow reasonable flexibility for better coverage
                score = 0
                
                # Street must match exactly for reliable strategy
                if estimated_street == target_street:
                    score += 15  # Street match is important
                else:
                    continue  # Skip if street doesn't match
                
                # Position matching with reasonable flexibility
                if is_preflop_heads_up:
                    if estimated_position == target_position and abs(estimated_players - target_players) <= 1:
                        score += 12  # Good position + player count match
                    elif estimated_position == target_position:
                        score += 8   # Position match only
                    elif abs(estimated_players - target_players) <= 1:
                        score += 5   # Player count match only
                else:
                    # For other situations, allow more position flexibility
                    if estimated_position == target_position:
                        score += 10
                    elif abs(estimated_position - target_position) <= 1:
                        score += 6
                    elif abs(estimated_position - target_position) <= 2:
                        score += 3
                
                # Accept matches with reasonable scoring
                if score >= 20:  # Balanced threshold for good coverage
                    candidates.append((hash_key, strategy, score))
                    
            except:
                continue  # Skip if hash parsing fails
        
        if candidates:
            # Sort by score and return best match if score is reasonable
            candidates.sort(key=lambda x: x[2], reverse=True)
            best_hash, best_strategy, score = candidates[0]
            
            if score >= 22:  # Reasonable threshold for component matching
                logger.info(f"🔧 Using component match: hash {best_hash} (score: {score}/22+)")
                return best_strategy
            else:
                logger.info(f"❌ Rejecting component match: score {score} too low (need ≥22)")
        
        return None

    def _is_extremely_aggressive_strategy(self, strategy):
        """
        Detect extremely aggressive strategies that should be rejected on river with weak hands.
        
        Args:
            strategy (dict): Strategy dictionary with action probabilities
            
        Returns:
            bool: True if strategy is extremely aggressive (>90% all-in or >80% total raise)
        """
        if not strategy:
            return False
        
        # Check for action_5 (all-in) probability
        allin_prob = strategy.get('action_5', 0.0)
        if allin_prob > 0.9:  # >90% all-in is extremely aggressive
            return True
        
        # Check total raise probability (action_2 + action_3 + action_4 + action_5)
        total_raise_prob = 0
        for action_key in ['action_2', 'action_3', 'action_4', 'action_5']:
            total_raise_prob += strategy.get(action_key, 0.0)
        
        if total_raise_prob > 0.8:  # >80% total raise is very aggressive
            return True
        
        return False
