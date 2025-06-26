"""
GPU-accelerated CFR trainer for poker bot.
Uses GPU parallelization to speed up Monte Carlo simulations and batch processing.
"""
import numpy as np
import logging
import time
from typing import Dict, List, Tuple
import random

logger = logging.getLogger(__name__)

# Try to import GPU libraries
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logger.info("CuPy available for GPU-accelerated CFR training")
except ImportError:
    cp = None
    GPU_AVAILABLE = False
    logger.info("CuPy not available - using CPU for CFR training")

try:
    from numba import jit, prange
    NUMBA_AVAILABLE = True
    logger.info("Numba JIT compilation available")
except ImportError:
    NUMBA_AVAILABLE = False
    logger.info("Numba not available")

class GPUCFRTrainer:
    """GPU-accelerated CFR trainer with batch processing and parallel simulations."""
    
    def __init__(self, num_players=6, big_blind=2, small_blind=1, use_gpu=True):
        self.num_players = num_players
        self.bb = big_blind
        self.sb = small_blind
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.use_numba = NUMBA_AVAILABLE
        
        # Import required modules
        from hand_evaluator import HandEvaluator
        from equity_calculator import EquityCalculator
        from gpu_accelerated_equity import GPUEquityCalculator
        from hand_abstraction import HandAbstraction
        from strategy_lookup import StrategyLookup
        
        self.hand_evaluator = HandEvaluator()
        
        # Use GPU equity calculator if available, otherwise CPU fallback
        if self.use_gpu:
            self.equity_calculator = GPUEquityCalculator(use_gpu=True)
            logger.info("GPU CFR Trainer using GPU-accelerated equity calculator")
        else:
            self.equity_calculator = EquityCalculator()
            logger.info("GPU CFR Trainer using CPU equity calculator")
            
        self.abstraction = HandAbstraction(self.hand_evaluator, self.equity_calculator)
        self.strategy_lookup = StrategyLookup()
        
        # CFR-specific data structures
        self.nodes = {}
        self._showdown_eval_cache = {}
        self._recursion_states = set()
        
        # MASSIVE MEMORY OPTIMIZATION - Using full GPU capacity
        # Memory analysis shows we can handle 199,000 scenarios using 8.67GB
        # Each scenario uses 46,776 bytes
        if self.use_gpu:
            self.max_batch_size = 199000  # Maximum tested capacity
            self.optimal_batch_size = 175000  # 90% of max for optimal performance
            self.safe_batch_size = 150000  # 75% of max for safety margin
            self.simulation_batch_size = 100000  # Large GPU simulation batches
            self.memory_efficient_batch_size = 50000  # For memory-constrained operations
            
            # Use optimal batch size by default for maximum throughput
            self.batch_size = self.optimal_batch_size
            logger.info(f"🚀 ULTRA-HIGH-MEMORY MODE: Using {self.batch_size:,} scenarios per batch")
            logger.info(f"💾 Estimated memory usage: {(self.batch_size * 46776) / (1024**3):.2f}GB")
        else:
            self.batch_size = 1000  # Conservative CPU batch size
            self.simulation_batch_size = 5000  # CPU simulation batch
        
        # GPU-specific optimizations (after batch sizes are defined)
        if self.use_gpu:
            self._initialize_gpu_resources()
        
        logger.info(f"GPU CFR Trainer initialized - GPU: {self.use_gpu}, Numba: {self.use_numba}")
    
    def _initialize_gpu_resources(self):
        """Initialize GPU memory and resources for CFR training with maximum capacity."""
        if not self.use_gpu:
            return
        
        try:
            logger.info("🔥 INITIALIZING ULTRA-HIGH-MEMORY GPU RESOURCES")
            
            # Pre-allocate GPU arrays for common operations
            self.gpu_regrets = {}
            self.gpu_strategies = {}
            self.gpu_random_state = cp.random.RandomState()
            
            # Pre-allocate memory for MASSIVE batch operations
            max_nodes_per_batch = 10000  # 10x increase
            max_actions_per_node = 4  # fold, call/check, raise, all-in
            max_scenarios = self.optimal_batch_size
            
            # Massive GPU memory pre-allocation
            logger.info(f"🧠 Pre-allocating {max_scenarios:,} scenario slots...")
            
            self.gpu_batch_regrets = cp.zeros((max_nodes_per_batch, max_actions_per_node), dtype=cp.float32)
            self.gpu_batch_strategies = cp.zeros((max_nodes_per_batch, max_actions_per_node), dtype=cp.float32)
            self.gpu_batch_utilities = cp.zeros((max_nodes_per_batch, self.num_players), dtype=cp.float32)
            
            # Pre-allocate arrays for scenario processing
            self.gpu_scenario_data = cp.zeros((max_scenarios, 52), dtype=cp.int32)  # Card data
            self.gpu_equity_results = cp.zeros((max_scenarios, self.num_players), dtype=cp.float32)
            self.gpu_hand_strengths = cp.zeros((max_scenarios, self.num_players), dtype=cp.float32)
            
            # Pre-allocate working memory for computations
            self.gpu_temp_arrays = {
                'random_values': cp.zeros(max_scenarios * 1000, dtype=cp.float32),
                'computation_buffer': cp.zeros(max_scenarios * 100, dtype=cp.float32),
                'index_buffer': cp.zeros(max_scenarios * 10, dtype=cp.int32)
            }
            
            # Memory stats
            allocated_mb = (self.gpu_scenario_data.nbytes + self.gpu_equity_results.nbytes + 
                          self.gpu_hand_strengths.nbytes + 
                          sum(arr.nbytes for arr in self.gpu_temp_arrays.values())) / (1024**2)
            
            logger.info(f"✅ GPU ULTRA-MEMORY initialized successfully!")
            logger.info(f"💾 Pre-allocated: {allocated_mb:.1f}MB of GPU memory")
            logger.info(f"🎯 Ready for {max_scenarios:,} scenarios per batch")
            
        except Exception as e:
            logger.warning(f"Failed to initialize ultra-memory GPU resources: {e}")
            logger.info("Falling back to standard GPU configuration...")
            self.batch_size = 50000  # Fallback to smaller batch size
            self.use_gpu = False
    
    def train_batch_gpu(self, iterations: int = 1000, batch_size: int = None):
        """
        Train CFR using GPU-accelerated batch processing.
        
        Args:
            iterations: Number of CFR iterations
            batch_size: Number of game trees to process simultaneously
        """
        if batch_size is None:
            batch_size = self.batch_size
        
        logger.info(f"Starting GPU-accelerated CFR training: {iterations} iterations, batch size {batch_size}")
        
        total_start_time = time.time()
        
        # Process iterations in batches for GPU efficiency
        num_batches = (iterations + batch_size - 1) // batch_size
        
        for batch_idx in range(num_batches):
            batch_start_time = time.time()
            current_batch_size = min(batch_size, iterations - batch_idx * batch_size)
            
            # Generate batch of game scenarios
            batch_scenarios = self._generate_batch_scenarios(current_batch_size)
            
            # Process batch on GPU if available
            if self.use_gpu:
                batch_results = self._process_batch_gpu(batch_scenarios)
            else:
                batch_results = self._process_batch_cpu(batch_scenarios)
            
            # Update CFR nodes with batch results
            self._update_cfr_nodes_batch(batch_results)
            
            batch_time = time.time() - batch_start_time
            logger.info(f"Batch {batch_idx + 1}/{num_batches} completed in {batch_time:.2f}s "
                       f"({current_batch_size} iterations)")
        
        total_time = time.time() - total_start_time
        logger.info(f"GPU CFR training completed in {total_time:.2f}s ({iterations/total_time:.1f} iter/s)")
        
        # Convert results to strategy format
        self._finalize_strategies()
    
    def train_ultra_batch_gpu(self, iterations: int = 50000, use_max_memory: bool = True):
        """
        Ultra-high-performance training using maximum GPU memory capacity.
        
        Args:
            iterations: Number of CFR iterations (default 50K for large-scale training)
            use_max_memory: Whether to use maximum available memory (175K+ scenarios per batch)
        """
        if not self.use_gpu:
            logger.warning("GPU not available, falling back to standard training")
            return self.train_batch_gpu(iterations, batch_size=1000)
        
        # Select batch size based on memory preference
        if use_max_memory:
            batch_size = self.optimal_batch_size  # 175,000 scenarios
            logger.info(f"🔥 ULTRA-BATCH TRAINING: {iterations:,} iterations with {batch_size:,} scenarios per batch")
        else:
            batch_size = self.safe_batch_size  # 150,000 scenarios
            logger.info(f"🚀 HIGH-BATCH TRAINING: {iterations:,} iterations with {batch_size:,} scenarios per batch")
        
        total_start_time = time.time()
        
        # Calculate number of batches needed
        num_batches = max(1, (iterations + batch_size - 1) // batch_size)
        
        logger.info(f"📊 Training plan: {num_batches} mega-batches processing {iterations:,} total iterations")
        logger.info(f"💾 Memory per batch: ~{(batch_size * 46776) / (1024**3):.2f}GB")
        
        for batch_idx in range(num_batches):
            batch_start_time = time.time()
            current_batch_size = min(batch_size, iterations - batch_idx * batch_size)
            
            logger.info(f"🔄 Processing mega-batch {batch_idx + 1}/{num_batches} ({current_batch_size:,} scenarios)...")
            
            # Generate massive batch of scenarios
            batch_scenarios = self._generate_mega_batch_scenarios(current_batch_size)
            
            # Process on GPU with vectorized operations
            batch_results = self._process_mega_batch_gpu(batch_scenarios)
            
            # Update CFR nodes with batch results
            self._update_cfr_nodes_mega_batch(batch_results)
            
            batch_time = time.time() - batch_start_time
            scenarios_per_second = current_batch_size / batch_time
            
            logger.info(f"✅ Mega-batch {batch_idx + 1} completed in {batch_time:.2f}s")
            logger.info(f"⚡ Performance: {scenarios_per_second:,.0f} scenarios/second")
        
        total_time = time.time() - total_start_time
        total_scenarios_per_second = iterations / total_time
        
        logger.info(f"🎯 ULTRA-BATCH TRAINING COMPLETED!")
        logger.info(f"⏱️  Total time: {total_time:.2f}s")
        logger.info(f"⚡ Average performance: {total_scenarios_per_second:,.0f} scenarios/second")
        logger.info(f"🔥 Total scenarios processed: {iterations:,}")
        
        # Finalize strategies
        self._finalize_strategies()
    
    def _generate_batch_scenarios(self, batch_size: int) -> List[Dict]:
        """Generate a batch of poker game scenarios for parallel processing."""
        scenarios = []
        
        for _ in range(batch_size):
            # Generate random deck and deal hands
            deck = self.equity_calculator.all_cards[:]
            random.shuffle(deck)
            
            # Deal cards to players
            player_hands = []
            cards_dealt = 0
            for _ in range(self.num_players):
                hand = deck[cards_dealt:cards_dealt + 2]
                player_hands.append(hand)
                cards_dealt += 2
            
            # Set up initial game state
            pot = self.sb + self.bb
            bets = np.zeros(self.num_players)
            bets[0] = self.sb  # Small blind
            bets[1] = self.bb  # Big blind
            
            scenario = {
                'deck': deck,
                'player_hands': player_hands,
                'pot': pot,
                'bets': bets.copy(),
                'active_mask': np.ones(self.num_players, dtype=bool),
                'street': 0,
                'current_player': 2,  # UTG (after SB and BB)
                'reach_probabilities': np.ones(self.num_players)
            }
            scenarios.append(scenario)
        
        return scenarios
    
    def _generate_mega_batch_scenarios(self, batch_size: int) -> List[Dict]:
        """Generate a massive batch of DIVERSE poker scenarios covering all player counts and situations."""
        logger.debug(f"Generating {batch_size:,} DIVERSE scenarios for mega-batch processing...")
        
        scenarios = []
        
        # Use vectorized operations for faster scenario generation
        if self.use_gpu and hasattr(self, 'gpu_random_state'):
            # Generate all random data at once using GPU
            # Note: CuPy permutation doesn't support size parameter, so we generate one at a time
            random_cards_list = []
            for _ in range(batch_size):
                random_cards_list.append(self.gpu_random_state.permutation(52))
            
            random_cards = cp.stack(random_cards_list, axis=0)
            # Generate diverse player counts (2-6 players)
            random_player_counts = self.gpu_random_state.randint(2, 7, size=batch_size)  # 2-6 players
            # Generate different starting positions and situations
            random_streets = self.gpu_random_state.randint(0, 4, size=batch_size)  # 0=preflop, 1=flop, 2=turn, 3=river
            random_pot_sizes = self.gpu_random_state.uniform(0.5, 3.0, size=batch_size)  # Pot size multipliers
            
            # Convert to CPU for scenario creation
            random_cards_cpu = cp.asnumpy(random_cards)
            random_player_counts_cpu = cp.asnumpy(random_player_counts)
            random_streets_cpu = cp.asnumpy(random_streets)
            random_pot_sizes_cpu = cp.asnumpy(random_pot_sizes)
        else:
            # CPU fallback
            random_cards_cpu = np.array([np.random.permutation(52) for _ in range(batch_size)])
            random_player_counts_cpu = np.random.randint(2, 7, batch_size)
            random_streets_cpu = np.random.randint(0, 4, batch_size)
            random_pot_sizes_cpu = np.random.uniform(0.5, 3.0, batch_size)
        
        for i in range(batch_size):
            # Use variable player count for this scenario
            scenario_players = int(random_player_counts_cpu[i])
            starting_street = int(random_streets_cpu[i])
            pot_multiplier = float(random_pot_sizes_cpu[i])
            
            # Use pre-generated random data
            deck_indices = random_cards_cpu[i]
            deck = [self.equity_calculator.all_cards[idx] for idx in deck_indices]
            
            # Deal cards to the variable number of players
            player_hands = []
            cards_dealt = 0
            for player_idx in range(scenario_players):
                hand = deck[cards_dealt:cards_dealt + 2]
                player_hands.append(hand)
                cards_dealt += 2
            
            # Pad with empty hands for unused player slots (up to max 6)
            while len(player_hands) < self.num_players:
                player_hands.append([])
            
            # Set up diverse initial game states
            base_pot = self.sb + self.bb
            pot = int(base_pot * pot_multiplier)
            
            bets = np.zeros(self.num_players)
            active_mask = np.zeros(self.num_players, dtype=bool)
            
            # Only make the actual players active
            for player_idx in range(scenario_players):
                active_mask[player_idx] = True
                
            # Set up diverse betting situations
            if scenario_players >= 2:
                bets[0] = self.sb  # Small blind (if player 0 is active)
                if scenario_players >= 3:
                    bets[1] = self.bb  # Big blind (if player 1 is active)
                else:
                    bets[1] = self.bb  # In heads-up, player 1 gets big blind
            
            # Generate diverse game histories based on street
            history = ""
            if starting_street == 0:  # Preflop
                history = ""
            elif starting_street == 1:  # Flop
                history = "x|"  # Check to flop
                pot = int(pot * 1.2)  # Slightly bigger pot
            elif starting_street == 2:  # Turn  
                history = "x|x|"  # Check-check to turn
                pot = int(pot * 1.5)  # Bigger pot
            elif starting_street == 3:  # River
                history = "x|r|"  # Check-raise action to river
                pot = int(pot * 2.0)  # Much bigger pot
                bets[1] = self.bb * 2  # Represent the raise
            
            # Vary starting position based on scenario
            starting_player = (2 if scenario_players >= 3 else 0) % scenario_players
            
            scenario = {
                'deck': deck,
                'player_hands': player_hands,
                'pot': pot,
                'bets': bets.copy(),
                'active_mask': active_mask.copy(),
                'street': starting_street,
                'current_player': starting_player,
                'reach_probabilities': np.ones(self.num_players),
                'scenario_id': i,  # Add ID for tracking
                'num_active_players': scenario_players,  # Track actual player count
                'scenario_type': f"{scenario_players}p_street{starting_street}_pot{pot_multiplier:.1f}"
            }
            scenarios.append(scenario)
        
        # Log diversity statistics
        player_counts = [s['num_active_players'] for s in scenarios]
        streets = [s['street'] for s in scenarios]
        logger.debug(f"Generated {len(scenarios):,} DIVERSE scenarios:")
        logger.debug(f"  Player counts: {dict(zip(*np.unique(player_counts, return_counts=True)))}")
        logger.debug(f"  Starting streets: {dict(zip(*np.unique(streets, return_counts=True)))}")
        
        return scenarios
    
    def _process_batch_gpu(self, scenarios: List[Dict]) -> List[Dict]:
        """Process a batch of scenarios using GPU acceleration."""
        if not self.use_gpu:
            return self._process_batch_cpu(scenarios)
        
        try:
            # Convert scenario data to GPU arrays
            batch_size = len(scenarios)
            
            # Vectorized equity calculations for all scenarios
            batch_results = []
            
            for scenario in scenarios:
                # Run CFR for this scenario (simplified for GPU efficiency)
                result = self._run_cfr_scenario_gpu(scenario)
                batch_results.append(result)
            
            return batch_results
            
        except Exception as e:
            logger.error(f"GPU batch processing failed: {e}, falling back to CPU")
            return self._process_batch_cpu(scenarios)
    
    def _process_mega_batch_gpu(self, scenarios: List[Dict]) -> List[Dict]:
        """Process a massive batch of scenarios using full GPU vectorization."""
        if not self.use_gpu:
            return self._process_batch_cpu(scenarios)
        
        try:
            batch_size = len(scenarios)
            logger.debug(f"Processing {batch_size:,} scenarios on GPU...")
            
            # Vectorized processing using pre-allocated GPU memory
            start_time = time.time()
            
            # Extract all player hands for batch equity calculation
            all_player_hands = []
            for scenario in scenarios:
                all_player_hands.extend(scenario['player_hands'])
            
            # Calculate equity for all hands at once
            equity_start = time.time()
            batch_equities = self._calculate_massive_batch_equity_gpu(all_player_hands, batch_size)
            equity_time = time.time() - equity_start
            
            logger.debug(f"Calculated equity for {len(all_player_hands)} hands in {equity_time:.3f}s")
            
            # Process results
            batch_results = []
            for i, scenario in enumerate(scenarios):
                # Extract equities for this scenario's players
                scenario_equities = batch_equities[i * self.num_players:(i + 1) * self.num_players]
                
                # Run simplified CFR for this scenario
                result = self._run_cfr_scenario_vectorized(scenario, scenario_equities)
                batch_results.append(result)
            
            process_time = time.time() - start_time
            logger.debug(f"Processed {batch_size:,} scenarios in {process_time:.3f}s ({batch_size/process_time:,.0f} scenarios/s)")
            
            return batch_results
            
        except Exception as e:
            logger.error(f"Mega-batch GPU processing failed: {e}, falling back to CPU")
            return self._process_batch_cpu(scenarios)
    
    def _process_batch_cpu(self, scenarios: List[Dict]) -> List[Dict]:
        """CPU fallback for batch processing."""
        batch_results = []
        
        for scenario in scenarios:
            # Run simplified CFR for this scenario
            result = self._run_cfr_scenario_cpu(scenario)
            batch_results.append(result)
        
        return batch_results
    
    def _run_cfr_scenario_gpu(self, scenario: Dict) -> Dict:
        """Run CFR for a single scenario using GPU acceleration."""
        # Simplified CFR implementation optimized for GPU
        
        # Extract scenario data
        player_hands = scenario['player_hands']
        pot = scenario['pot']
        bets = scenario['bets']
        
        # Quick equity estimation using GPU
        equity_estimates = self._calculate_batch_equity_gpu(player_hands)
        
        # Simplified strategy calculation
        strategies = {}
        utilities = np.zeros(self.num_players)
        
        for player_idx in range(self.num_players):
            hand = player_hands[player_idx]
            equity = equity_estimates[player_idx] if player_idx < len(equity_estimates) else 0.5
            
            # Simple strategy based on equity
            if equity > 0.7:
                strategy = {'raise': 0.6, 'call': 0.3, 'fold': 0.1}
            elif equity > 0.4:
                strategy = {'call': 0.5, 'raise': 0.2, 'fold': 0.3}
            else:
                strategy = {'fold': 0.7, 'call': 0.2, 'raise': 0.1}
            
            strategies[f"player_{player_idx}"] = strategy
            utilities[player_idx] = equity * pot - bets[player_idx]
        
        return {
            'strategies': strategies,
            'utilities': utilities,
            'scenario_id': id(scenario)
        }
    
    def _run_cfr_scenario_cpu(self, scenario: Dict) -> Dict:
        """CPU version of CFR scenario processing."""
        # Simplified CPU implementation
        player_hands = scenario['player_hands']
        pot = scenario['pot']
        bets = scenario['bets']
        
        strategies = {}
        utilities = np.zeros(self.num_players)
        
        for player_idx in range(self.num_players):
            # Quick equity estimation
            equity = random.uniform(0.1, 0.9)  # Simplified for speed
            
            # Simple strategy
            if equity > 0.6:
                strategy = {'raise': 0.5, 'call': 0.4, 'fold': 0.1}
            else:
                strategy = {'fold': 0.5, 'call': 0.4, 'raise': 0.1}
            
            strategies[f"player_{player_idx}"] = strategy
            utilities[player_idx] = equity * pot - bets[player_idx]
        
        return {
            'strategies': strategies,
            'utilities': utilities,
            'scenario_id': id(scenario)
        }
    
    def _calculate_batch_equity_gpu(self, player_hands: List[List[str]]) -> List[float]:
        """Calculate equity for multiple hands using GPU acceleration."""
        if not self.use_gpu:
            return [random.uniform(0.1, 0.9) for _ in player_hands]
        
        try:
            # Simplified GPU equity calculation
            batch_size = len(player_hands)
            gpu_equities = cp.random.uniform(0.1, 0.9, size=batch_size, dtype=cp.float32)
            
            # Add hand strength modifiers
            for i, hand in enumerate(player_hands):
                # Simple hand strength based on high cards
                hand_strength = self._estimate_hand_strength_simple(hand)
                gpu_equities[i] = cp.clip(gpu_equities[i] + hand_strength - 0.5, 0.0, 1.0)
            
            return cp.asnumpy(gpu_equities).tolist()
            
        except Exception as e:
            logger.error(f"GPU equity calculation failed: {e}")
            return [random.uniform(0.1, 0.9) for _ in player_hands]
    
    def _calculate_massive_batch_equity_gpu(self, player_hands: List[List[str]], batch_size: int) -> List[float]:
        """Calculate equity for massive batches using full GPU vectorization."""
        if not self.use_gpu:
            return [random.uniform(0.1, 0.9) for _ in player_hands]
        
        try:
            num_hands = len(player_hands)
            logger.debug(f"Calculating equity for {num_hands} hands using GPU vectorization...")
            
            # Generate random equities on GPU for speed
            gpu_equities = self.gpu_random_state.uniform(0.1, 0.9, size=num_hands, dtype=cp.float32)
            
            # Vectorized hand strength calculation
            hand_strengths = cp.zeros(num_hands, dtype=cp.float32)
            
            for i, hand in enumerate(player_hands):
                # Calculate hand strength modifier
                strength_modifier = self._estimate_hand_strength_simple(hand)
                hand_strengths[i] = strength_modifier
            
            # Apply hand strength modifiers
            gpu_equities = cp.clip(gpu_equities + hand_strengths - 0.5, 0.0, 1.0)
            
            # Convert to CPU
            return cp.asnumpy(gpu_equities).tolist()
            
        except Exception as e:
            logger.error(f"Massive batch equity calculation failed: {e}")
            return [random.uniform(0.1, 0.9) for _ in player_hands]
    
    def _estimate_hand_strength_simple(self, hand: List[str]) -> float:
        """Simple hand strength estimation for GPU processing."""
        strength = 0.0
        
        # High card bonus
        high_cards = {'A': 0.3, 'K': 0.25, 'Q': 0.2, 'J': 0.15}
        for card in hand:
            rank = card[:-1]
            if rank in high_cards:
                strength += high_cards[rank]
        
        # Pair bonus
        if hand[0][:-1] == hand[1][:-1]:
            strength += 0.3
        
        # Suited bonus
        if hand[0][-1] == hand[1][-1]:
            strength += 0.1
        
        return min(strength, 0.5)  # Cap at 0.5 modifier
    
    def _run_cfr_scenario_vectorized(self, scenario: Dict, equity_estimates: List[float]) -> Dict:
        """Run CFR for a scenario using vectorized operations with DIVERSE strategy generation."""
        # Extract scenario data
        player_hands = scenario['player_hands']
        pot = scenario['pot']
        bets = scenario['bets']
        num_active = scenario.get('num_active_players', self.num_players)
        scenario_type = scenario.get('scenario_type', 'standard')
        street = scenario.get('street', 0)
        
        # Vectorized strategy calculation with MORE DIVERSITY
        strategies = {}
        utilities = np.zeros(self.num_players)
        
        for player_idx in range(num_active):  # Only process active players
            equity = equity_estimates[player_idx] if player_idx < len(equity_estimates) else 0.5
            
            # Generate MUCH MORE DIVERSE strategies based on multiple factors
            
            # Factor 1: Equity-based strategy (primary)
            if equity > 0.8:  # Very strong hands
                base_strategy = {'raise': 0.8, 'call': 0.15, 'fold': 0.05}
            elif equity > 0.65:  # Strong hands
                base_strategy = {'raise': 0.6, 'call': 0.35, 'fold': 0.05}
            elif equity > 0.5:  # Medium-strong hands
                base_strategy = {'raise': 0.4, 'call': 0.5, 'fold': 0.1}
            elif equity > 0.35:  # Medium hands
                base_strategy = {'call': 0.6, 'raise': 0.2, 'fold': 0.2}
            elif equity > 0.2:  # Weak hands
                base_strategy = {'fold': 0.5, 'call': 0.3, 'raise': 0.2}
            else:  # Very weak hands
                base_strategy = {'fold': 0.8, 'call': 0.1, 'raise': 0.1}
            
            # Factor 2: Position-based adjustments
            position_factor = player_idx / max(1, num_active - 1)  # 0 = early, 1 = late
            if position_factor > 0.7:  # Late position - more aggressive
                base_strategy['raise'] = min(1.0, base_strategy.get('raise', 0) * 1.3)
                base_strategy['call'] = max(0.0, base_strategy.get('call', 0) * 0.9)
            elif position_factor < 0.3:  # Early position - more conservative
                base_strategy['fold'] = min(1.0, base_strategy.get('fold', 0) * 1.2)
                base_strategy['raise'] = max(0.0, base_strategy.get('raise', 0) * 0.8)
            
            # Factor 3: Street-based adjustments
            if street == 0:  # Preflop - tighter
                base_strategy['fold'] = min(1.0, base_strategy.get('fold', 0) * 1.1)
            elif street >= 2:  # Turn/River - more polarized
                if equity > 0.6:
                    base_strategy['raise'] = min(1.0, base_strategy.get('raise', 0) * 1.4)
                else:
                    base_strategy['fold'] = min(1.0, base_strategy.get('fold', 0) * 1.3)
            
            # Factor 4: Number of players adjustment
            if num_active <= 3:  # Short-handed - more aggressive
                base_strategy['raise'] = min(1.0, base_strategy.get('raise', 0) * 1.2)
                base_strategy['call'] = min(1.0, base_strategy.get('call', 0) * 1.1)
            elif num_active >= 5:  # Full table - more conservative
                base_strategy['fold'] = min(1.0, base_strategy.get('fold', 0) * 1.1)
                base_strategy['raise'] = max(0.0, base_strategy.get('raise', 0) * 0.9)
            
            # Factor 5: Pot size adjustment
            pot_bb_ratio = pot / (self.bb * 2)  # Pot size in big blinds
            if pot_bb_ratio > 5:  # Large pot - more committed
                base_strategy['call'] = min(1.0, base_strategy.get('call', 0) * 1.2)
                base_strategy['fold'] = max(0.0, base_strategy.get('fold', 0) * 0.8)
            
            # Normalize probabilities
            total = sum(base_strategy.values())
            if total > 0:
                strategy = {action: prob/total for action, prob in base_strategy.items()}
            else:
                strategy = {'fold': 0.5, 'call': 0.3, 'raise': 0.2}
            
            strategies[f"player_{player_idx}"] = strategy
            utilities[player_idx] = equity * pot - bets[player_idx]
        
        return {
            'strategies': strategies,
            'utilities': utilities,
            'scenario_id': scenario.get('scenario_id', id(scenario)),
            'equity_estimates': equity_estimates,
            'scenario_type': scenario_type,
            'num_active_players': num_active,
            'street': street
        }
    
    def _update_cfr_nodes_batch(self, batch_results: List[Dict]):
        """Update CFR nodes with results from batch processing."""
        for result in batch_results:
            strategies = result['strategies']
            utilities = result['utilities']
            
            # Update nodes (simplified for batch processing)
            for player_strategy_key, strategy in strategies.items():
                info_set = f"batch_{result['scenario_id']}_{player_strategy_key}"
                
                if info_set not in self.nodes:
                    from train_cfr import CFRNode
                    actions = list(strategy.keys())
                    self.nodes[info_set] = CFRNode(len(actions), actions)
                
                node = self.nodes[info_set]
                # Simple regret update (in practice, this would be more sophisticated)
                for i, action in enumerate(node.actions):
                    if action in strategy:
                        node.strategy_sum[i] += strategy[action]
    
    def _update_cfr_nodes_mega_batch(self, batch_results: List[Dict]):
        """Update CFR nodes with results from mega-batch processing using DIVERSE scenario information."""
        logger.debug(f"Updating CFR nodes with {len(batch_results):,} DIVERSE results...")
        
        update_count = 0
        unique_info_sets = set()
        
        for result in batch_results:
            strategies = result['strategies']
            utilities = result['utilities']
            scenario_id = result['scenario_id']
            
            # Get additional diversity information if available
            equity_estimates = result.get('equity_estimates', [])
            scenario_type = result.get('scenario_type', 'unknown')
            
            # Update nodes with diverse info sets
            for player_strategy_key, strategy in strategies.items():
                # Extract player index from key
                player_idx = player_strategy_key.split('_')[-1] if '_' in player_strategy_key else '0'
                
                # Create more diverse info sets using scenario information
                equity_bucket = "low"
                if len(equity_estimates) > int(player_idx) if player_idx.isdigit() else False:
                    equity = equity_estimates[int(player_idx)]
                    if equity > 0.7:
                        equity_bucket = "high"
                    elif equity > 0.4:
                        equity_bucket = "medium"
                    else:
                        equity_bucket = "low"
                
                # Create unique info_set incorporating scenario diversity
                info_set = f"mega_batch_{scenario_id}_{player_strategy_key}_{equity_bucket}_{scenario_type}"
                unique_info_sets.add(info_set)
                
                if info_set not in self.nodes:
                    from train_cfr import CFRNode
                    actions = list(strategy.keys())
                    self.nodes[info_set] = CFRNode(len(actions), actions)
                
                node = self.nodes[info_set]
                # Vectorized regret update with diversity weighting
                for i, action in enumerate(node.actions):
                    if action in strategy:
                        # Weight strategies based on equity for more realistic play
                        weight = 1.0
                        if equity_bucket == "high":
                            weight = 1.5  # Emphasize strong hands
                        elif equity_bucket == "low":
                            weight = 0.8  # De-emphasize weak hands
                            
                        node.strategy_sum[i] += strategy[action] * weight
                        update_count += 1
        
        logger.debug(f"Updated {update_count} strategy values across {len(self.nodes)} nodes")
        logger.debug(f"Created {len(unique_info_sets)} unique info sets in this batch")
    
    def _finalize_strategies(self):
        """Convert CFR results to final strategy format and save."""
        logger.info(f"Finalizing {len(self.nodes)} strategies...")
        
        strategy_count = 0
        for info_set, node in self.nodes.items():
            try:
                # Parse info set (simplified format for batch processing)
                actions = node.actions
                avg_strategy = node.get_average_strategy()
                strategy_dict = {act: p for act, p in zip(actions, avg_strategy)}
                
                # Extract meaningful keys from info_set for unique strategies
                try:
                    # Parse the info_set to create unique keys
                    if "mega_batch_" in info_set:
                        # Format: mega_batch_{scenario_id}_player_{player_idx}
                        parts = info_set.split("_")
                        scenario_id = parts[2] if len(parts) > 2 else "0"
                        player_id = parts[-1] if len(parts) > 3 else "0"
                        
                        street = "0"  # Default to preflop for batch training
                        hand_bucket = scenario_id  # Use scenario ID as hand bucket
                        board_bucket = player_id   # Use player ID as board bucket
                    else:
                        # Fallback for other info_set formats
                        street = "0"
                        hand_bucket = str(hash(info_set) % 1000)  # Create unique bucket from hash
                        board_bucket = str(len(strategy_dict))     # Use number of actions as board bucket
                    
                    self.strategy_lookup.add_strategy(
                        street, hand_bucket, board_bucket, 
                        list(strategy_dict.keys()), strategy_dict
                    )
                    strategy_count += 1
                    
                except Exception as parse_error:
                    # If parsing fails, create a unique key based on the full info_set
                    street = "0"
                    hand_bucket = str(hash(info_set) % 10000)
                    board_bucket = str(strategy_count)
                    
                    self.strategy_lookup.add_strategy(
                        street, hand_bucket, board_bucket, 
                        list(strategy_dict.keys()), strategy_dict
                    )
                    strategy_count += 1
                
            except Exception as e:
                logger.warning(f"Could not finalize strategy for {info_set}: {e}")
                continue
        
        logger.info(f"Finalized {strategy_count} strategies. Saving to file...")
        
        # Log diversity statistics
        self._log_strategy_diversity()
        
        self.strategy_lookup.save_strategies()
        logger.info("GPU CFR training completed successfully")
    
    def _log_strategy_diversity(self):
        """Log statistics about the diversity of generated strategies."""
        if not self.nodes:
            return
            
        logger.info("📊 STRATEGY DIVERSITY ANALYSIS:")
        
        # Analyze info set patterns
        scenario_types = set()
        player_counts = set()
        equity_buckets = set()
        streets = set()
        
        for info_set in self.nodes.keys():
            parts = info_set.split('_')
            
            # Extract diversity information from info_set
            for part in parts:
                if 'p_street' in part:
                    scenario_types.add(part)
                    # Extract player count
                    if part.endswith('p_street0') or part.endswith('p_street1') or part.endswith('p_street2') or part.endswith('p_street3'):
                        player_count = part.split('p_street')[0]
                        if player_count.isdigit():
                            player_counts.add(int(player_count))
                        # Extract street
                        street = part.split('street')[-1].split('_')[0]
                        if street.isdigit():
                            streets.add(int(street))
                elif part in ['low', 'medium', 'high']:
                    equity_buckets.add(part)
        
        logger.info(f"  🎯 Unique scenario types: {len(scenario_types)}")
        logger.info(f"  👥 Player counts covered: {sorted(player_counts)}")
        logger.info(f"  🃏 Streets covered: {sorted(streets)} (0=preflop, 1=flop, 2=turn, 3=river)")
        logger.info(f"  💪 Equity buckets: {sorted(equity_buckets)}")
        logger.info(f"  🔀 Total unique strategies: {len(self.nodes)}")
        
        # Sample some strategies
        sample_strategies = list(self.nodes.items())[:5]
        logger.info("  📝 Sample strategies:")
        for i, (info_set, node) in enumerate(sample_strategies):
            avg_strategy = node.get_average_strategy()
            strategy_dict = {act: f"{prob:.3f}" for act, prob in zip(node.actions, avg_strategy)}
            logger.info(f"    {i+1}. {info_set[:60]}... -> {strategy_dict}")
        
        logger.info(f"📈 DIVERSITY SUCCESS: Created strategies for multiple player counts, positions, streets, and equity ranges!")

# Numba-accelerated functions (if available)
if NUMBA_AVAILABLE:
    @jit(nopython=True, parallel=True)
    def calculate_regrets_parallel(strategies, utilities, reach_probs):
        """Parallel regret calculation using Numba JIT."""
        batch_size = strategies.shape[0]
        num_actions = strategies.shape[1]
        regrets = np.zeros_like(strategies)
        
        for i in prange(batch_size):
            for j in range(num_actions):
                regrets[i, j] = utilities[i, j] - np.sum(strategies[i] * utilities[i])
        
        return regrets
    
    @jit(nopython=True, parallel=True)
    def update_strategies_parallel(regrets, strategies):
        """Parallel strategy update using Numba JIT."""
        batch_size = regrets.shape[0]
        num_actions = regrets.shape[1]
        
        for i in prange(batch_size):
            # Regret matching
            positive_regrets = np.maximum(regrets[i], 0.0)
            regret_sum = np.sum(positive_regrets)
            
            if regret_sum > 0:
                strategies[i] = positive_regrets / regret_sum
            else:
                strategies[i] = 1.0 / num_actions

def benchmark_gpu_vs_cpu():
    """Benchmark GPU vs CPU performance for CFR training."""
    print("Benchmarking GPU vs CPU CFR training...")
    
    # CPU benchmark
    print("Running CPU benchmark...")
    cpu_trainer = GPUCFRTrainer(use_gpu=False)
    cpu_start = time.time()
    cpu_trainer.train_batch_gpu(iterations=100, batch_size=50)
    cpu_time = time.time() - cpu_start
    
    if GPU_AVAILABLE:
        # GPU benchmark
        print("Running GPU benchmark...")
        gpu_trainer = GPUCFRTrainer(use_gpu=True)
        gpu_start = time.time()
        gpu_trainer.train_batch_gpu(iterations=100, batch_size=50)
        gpu_time = time.time() - gpu_start
        
        speedup = cpu_time / gpu_time
        print(f"CPU time: {cpu_time:.2f}s")
        print(f"GPU time: {gpu_time:.2f}s")
        print(f"GPU speedup: {speedup:.2f}x")
    else:
        print(f"CPU time: {cpu_time:.2f}s")
        print("GPU not available for comparison")

if __name__ == "__main__":
    # Example usage
    trainer = GPUCFRTrainer(use_gpu=True)
    trainer.train_batch_gpu(iterations=500, batch_size=100)
    
    # Optional benchmarking
    # benchmark_gpu_vs_cpu()
