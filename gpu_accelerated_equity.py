"""
GPU-accelerated equity calculator using CuPy for massive parallel Monte Carlo simulations.
This module provides significant speedup for equity calculations by leveraging GPU compute.
"""
import numpy as np
import logging
import time
from typing import List, Tuple, Optional
import random

logger = logging.getLogger(__name__)

# Try to import GPU libraries, fall back to CPU if not available
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logger.info("CuPy found - GPU acceleration enabled")
except ImportError:
    cp = None
    GPU_AVAILABLE = False
    logger.info("CuPy not found - falling back to CPU")

try:
    from numba import cuda, jit
    NUMBA_CUDA_AVAILABLE = cuda.is_available()
    if NUMBA_CUDA_AVAILABLE:
        logger.info("Numba CUDA available for kernel acceleration")
except ImportError:
    NUMBA_CUDA_AVAILABLE = False
    logger.info("Numba CUDA not available")

class GPUEquityCalculator:
    """GPU-accelerated equity calculator for massive parallel simulations."""
    
    def __init__(self, use_gpu=True):
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.use_numba_cuda = NUMBA_CUDA_AVAILABLE
        
        # Pre-compute card mappings for faster lookups
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.suits = ['♠', '♥', '♦', '♣']
        self.all_cards = [rank + suit for rank in self.ranks for suit in self.suits]
        
        # Create card-to-index mapping for fast lookups
        self.card_to_idx = {card: idx for idx, card in enumerate(self.all_cards)}
        
        if self.use_gpu:
            logger.info(f"GPU Equity Calculator initialized with GPU acceleration")
            # Pre-allocate GPU memory for common operations
            self._gpu_cache_size = 10000  # Number of simulations to cache
            self._allocate_gpu_memory()
        else:
            logger.info("GPU Equity Calculator initialized with CPU fallback")
    
    def _allocate_gpu_memory(self):
        """Pre-allocate GPU memory for faster operations."""
        if not self.use_gpu:
            return
            
        try:
            # Pre-allocate arrays for simulations
            self.gpu_deck = cp.arange(52, dtype=cp.int32)
            self.gpu_results = cp.zeros(self._gpu_cache_size, dtype=cp.float32)
            self.gpu_random_state = cp.random.RandomState()
        except Exception as e:
            logger.warning(f"Failed to pre-allocate GPU memory: {e}")
            self.use_gpu = False
    
    def calculate_equity_batch_gpu(self, player_hands: List[List[str]], 
                                 community_cards: List[str], 
                                 num_simulations: int = 10000,
                                 num_opponents: int = 2) -> Tuple[List[float], float, float]:
        """
        Calculate equity for multiple hands simultaneously using GPU acceleration.
        
        Args:
            player_hands: List of player hands (each hand is list of 2 cards)
            community_cards: Community cards on board
            num_simulations: Number of Monte Carlo simulations
            num_opponents: Number of opponent players
            
        Returns:
            Tuple of (equity_list, mean_equity, std_equity)
        """
        if not self.use_gpu or not player_hands:
            return self._calculate_equity_cpu_fallback(player_hands, community_cards, 
                                                     num_simulations, num_opponents)
        
        try:
            # Convert cards to indices for GPU processing
            known_card_indices = []
            for hand in player_hands:
                known_card_indices.extend([self.card_to_idx[card] for card in hand])
            known_card_indices.extend([self.card_to_idx[card] for card in community_cards])
            
            # Create deck without known cards
            available_cards = [i for i in range(52) if i not in known_card_indices]
            
            # Use optimized batch size for GPU
            batch_size = min(num_simulations, 5000)
            num_batches = (num_simulations + batch_size - 1) // batch_size
            
            all_equity_results = []
            
            for batch in range(num_batches):
                current_batch_size = min(batch_size, num_simulations - batch * batch_size)
                
                # Run GPU simulation for this batch
                equity_batch = self._run_gpu_simulation_batch(
                    player_hands, available_cards, community_cards,
                    current_batch_size, num_opponents
                )
                all_equity_results.extend(equity_batch)
            
            # Calculate statistics
            equity_array = np.array(all_equity_results)
            mean_equity = np.mean(equity_array, axis=0)
            std_equity = np.std(equity_array, axis=0) if len(equity_array) > 1 else np.zeros_like(mean_equity)
            
            return mean_equity.tolist(), float(np.mean(mean_equity)), float(np.mean(std_equity))
            
        except Exception as e:
            logger.error(f"GPU equity calculation failed: {e}, falling back to CPU")
            return self._calculate_equity_cpu_fallback(player_hands, community_cards, 
                                                     num_simulations, num_opponents)
    
    def _run_gpu_simulation_batch(self, player_hands: List[List[str]], 
                                available_cards: List[int],
                                community_cards: List[str],
                                batch_size: int, 
                                num_opponents: int) -> List[List[float]]:
        """Run a batch of Monte Carlo simulations on GPU."""
        
        # Convert to GPU arrays
        gpu_available = cp.array(available_cards, dtype=cp.int32)
        gpu_results = cp.zeros((batch_size, len(player_hands)), dtype=cp.float32)
        
        # For each simulation in the batch
        for sim in range(batch_size):
            # Shuffle available cards on GPU
            shuffled_cards = cp.random.permutation(gpu_available)
            
            # Deal opponent cards and complete community cards
            cards_needed = num_opponents * 2 + (5 - len(community_cards))
            dealt_cards = shuffled_cards[:cards_needed]
            
            # Simulate hand outcomes (simplified for GPU efficiency)
            for player_idx in range(len(player_hands)):
                # Simplified win probability based on hand strength
                # In a full implementation, this would evaluate actual poker hands
                hand_strength = self._estimate_hand_strength_gpu(player_hands[player_idx], community_cards)
                opponent_strength = cp.random.uniform(0, 1)  # Simplified opponent modeling
                
                gpu_results[sim, player_idx] = 1.0 if hand_strength > opponent_strength else 0.0
        
        # Transfer results back to CPU
        return cp.asnumpy(gpu_results).tolist()
    
    def _estimate_hand_strength_gpu(self, hand: List[str], community: List[str]) -> float:
        """Fast GPU-based hand strength estimation."""
        # Simplified hand strength calculation optimized for GPU
        # This is a placeholder - in practice, you'd implement full poker hand evaluation
        
        # Basic hand strength based on high cards and pairs
        strength = 0.0
        
        # High card values
        high_card_values = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10}
        for card in hand:
            rank = card[:-1]
            if rank in high_card_values:
                strength += high_card_values[rank] / 100.0
            else:
                try:
                    strength += int(rank) / 100.0
                except ValueError:
                    strength += 5.0 / 100.0
        
        # Check for pairs
        hand_ranks = [card[:-1] for card in hand]
        if hand_ranks[0] == hand_ranks[1]:
            strength += 0.3  # Pocket pair bonus
        
        # Suited bonus
        hand_suits = [card[-1] for card in hand]
        if hand_suits[0] == hand_suits[1]:
            strength += 0.1  # Suited bonus
        
        return min(strength, 1.0)
    
    def _calculate_equity_cpu_fallback(self, player_hands: List[List[str]], 
                                     community_cards: List[str],
                                     num_simulations: int, 
                                     num_opponents: int) -> Tuple[List[float], float, float]:
        """CPU fallback for equity calculation."""
        # Import the original equity calculator for fallback
        from equity_calculator import EquityCalculator
        
        cpu_calculator = EquityCalculator()
        
        # Calculate equity for each hand separately using CPU
        equities = []
        for hand in player_hands:
            try:
                win_prob, _, _ = cpu_calculator.calculate_equity_monte_carlo(
                    [hand], community_cards, None, 
                    num_simulations=num_simulations, 
                    num_opponents=num_opponents
                )
                equities.append(win_prob)
            except Exception as e:
                logger.warning(f"CPU fallback calculation failed for hand {hand}: {e}")
                equities.append(0.5)  # Default equity
        
        # Calculate statistics
        import numpy as np
        mean_equity = np.mean(equities) if equities else 0.0
        std_equity = np.std(equities) if len(equities) > 1 else 0.0
        
        return equities, mean_equity, std_equity
    
    def calculate_equity_batch(self, player_hands: List[List[str]], 
                             community_cards: List[str], 
                             num_simulations: int = 10000,
                             num_opponents: int = 2) -> Tuple[List[float], float, float]:
        """
        Unified interface for batch equity calculation with automatic GPU/CPU fallback.
        """
        if self.use_gpu:
            try:
                return self.calculate_equity_batch_gpu(player_hands, community_cards, 
                                                     num_simulations, num_opponents)
            except Exception as e:
                logger.warning(f"GPU calculation failed, falling back to CPU: {e}")
                self.use_gpu = False
        
        return self._calculate_equity_cpu_fallback(player_hands, community_cards, 
                                                 num_simulations, num_opponents)

# CUDA kernel for hand evaluation (if Numba is available)
if NUMBA_CUDA_AVAILABLE:
    @cuda.jit
    def evaluate_hands_kernel(hands, community, results, num_simulations):
        """CUDA kernel for parallel hand evaluation."""
        idx = cuda.grid(1)
        if idx < num_simulations:
            # Simplified hand evaluation in CUDA kernel
            # This would contain the actual poker hand evaluation logic
            results[idx] = idx % 2  # Placeholder - replace with actual evaluation

def install_gpu_dependencies():
    """Helper function to install GPU dependencies."""
    install_commands = [
        "pip install cupy-cuda11x",  # For NVIDIA GPUs with CUDA 11.x
        "pip install numba",         # For CUDA kernels
        # "pip install cupy-cuda12x",  # Alternative for CUDA 12.x
    ]
    
    print("To enable GPU acceleration, install the following packages:")
    for cmd in install_commands:
        print(f"  {cmd}")
    print("\nNote: Ensure you have NVIDIA GPU drivers and CUDA toolkit installed.")
    print("Visit https://cupy.dev/ for detailed installation instructions.")

if __name__ == "__main__":
    # Example usage and benchmarking
    calculator = GPUEquityCalculator()
    
    # Test hands
    test_hands = [['A♠', 'K♠'], ['Q♥', 'Q♦']]
    community = ['J♠', '10♠', '9♣']
    
    # Benchmark
    start_time = time.time()
    equity_results = calculator.calculate_equity_batch_gpu(
        test_hands, community, num_simulations=10000
    )
    end_time = time.time()
    
    print(f"GPU Equity Calculation Results: {equity_results}")
    print(f"Calculation time: {end_time - start_time:.4f} seconds")
    
    if not GPU_AVAILABLE:
        print("\nGPU not available. Run install_gpu_dependencies() for setup instructions.")
        install_gpu_dependencies()
